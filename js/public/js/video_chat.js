(async function () {
  async function main() {
    /* The HTML nodes used for rendering. */
    // const localVideoNode = document.querySelector("#localVideo");
    // const remoteVideoNode = document.querySelector("#remoteVideo");
    const localTranscriptNode = document.querySelector("#localTranscript");
    // const remoteTranscriptNode = document.querySelector("#remoteTranscript");
    const shareNode = document.querySelector("#urlShare");
    const editOnGlitchNode = document.querySelector("#editOnGlitch");
    if (
      // localVideoNode instanceof HTMLVideoElement &&
      // remoteVideoNode instanceof HTMLVideoElement &&
      localTranscriptNode instanceof HTMLElement &&
      // remoteTranscriptNode instanceof HTMLElement &&
      shareNode instanceof HTMLElement &&
      editOnGlitchNode instanceof HTMLAnchorElement
    ) {
      initEditGlitch(editOnGlitchNode);

      const socket = io.connect(window.location.origin);

      // Request access to the user's microphone and camera.
      let localStream;
      try {
        localStream = await navigator.mediaDevices.getUserMedia({
          audio: true,
          // video: { facingMode: "user" },
        });
      } catch {
        alert(
          "No microphone found. Please activate your microphone and refresh the page."
        );
        return;
      }

      // localVideoNode.srcObject = localStream;

      initRoom(shareNode, socket);
      // setupRemoteVideo(socket, localStream, remoteVideoNode);
      setupRealtimeTranscription(
        socket,
        localTranscriptNode,
        // remoteTranscriptNode
      );
    } else {
      console.error("one of the HTML nodes was not set up correctly");
      return;
    }
  }

  /**
   * @param {SocketIOClient.Socket} socket
   * The socket used to send the audio stream and get back the transcription.
   * @param {HTMLElement} localTranscriptNode
   * The HTML node used to display the local transcription.
   * @param {HTMLElement} remoteTranscriptNode
   * The HTML node used to display the remote transcription.
   */
  function setupRealtimeTranscription(
    socket,
    localTranscriptNode,
    // remoteTranscriptNode
  ) {
    const sampleRate = 16000;

    // Configure the recorder. The "Recorder" value is loaded in `index.html`
    // with the <script src="/js/recorder.min.js"> tag.
    const recorder = new Recorder({
      encoderPath: "/js/encoderWorker.min.js",
      leaveStreamOpen: true,
      numberOfChannels: 1,

      // OPUS options
      encoderSampleRate: sampleRate,
      streamPages: true,
      maxBuffersPerPage: 1,
    });

    /** We must forward the very first audio packet from the client because
     * it contains some header data needed for audio decoding.
     *
     * Thus, we must wait for the server to be ready before we start recording.
     */
    socket.on("can-open-mic", () => {
      recorder.start();
    });

    /** We forward our audio stream to the server. */
    recorder.ondataavailable = (e) => {
      socket.emit("microphone-stream", e.buffer);
    };

    const localTranscript = new Transcript();
    // const remoteTranscript = new Transcript();

    /** As Deepgram returns real-time transcripts, we display them back in the DOM.
     * @param {string} socketId
     * @param {any} jsonFromServer
     */
    socket.on("transcript-result", (socketId, jsonFromServer) => {
      if (socketId === socket.id) {
        localTranscript.addServerAnswer(jsonFromServer);
        var words = JSON.parse(jsonFromServer).channel.alternatives[0]
          .transcript
        if (words.length > 0) {
          localTranscriptNode.innerHTML = "";
          localTranscriptNode.appendChild(localTranscript.toHtml());
        }
        // if (words.length > 0) {
        //   localTranscriptNode.innerHTML += localTranscript.toHtml().innerHTML;
        // }
      }
    });
  }

  /** The server will send multiple messages that correspond to
   * the same chunk of audio, improving the transcription on each
   * message. The following class is a helper to keep track
   * of the current state of the transcript.
   */
  class Transcript {
    constructor() {
      /** @type {Map<number, {word: string, is_final: boolean, speaker: Number}>} */
      this.chunks = new Map();
    }

    /** @argument {any} jsonFromServer */
    addServerAnswer(jsonFromServer) {
      const json = JSON.parse(jsonFromServer);
      const transcript = json.channel.alternatives[0]
        .transcript;
      if (transcript !== "") {
        console.log(json);
      }
      json.channel.alternatives[0].words.forEach((element) => {
        this.chunks.set(
          element.start, {
          word: element.punctuated_word,
          is_final: json.is_final,
          speaker: element.speaker,
        }
        )
      });
      // this.chunks.set(json.start, {
      //   words,
      //   // if "is_final" is true, we will never have future updates for this
      //   // audio chunk.
      //   is_final: json.is_final,
      // });
    }


    /** @returns {HTMLElement} */
    toHtml() {
      const divNode = document.createElement("div");
      var prevSpeaker = -1;
      divNode.className = "transcript-text";
      [...this.chunks.entries()]
        .sort((entryA, entryB) => entryA[0] - entryB[0])
        .forEach((entry) => {
          var currSpeaker = entry[1].speaker;
          if (currSpeaker !== prevSpeaker) {
            if (prevSpeaker > -1) { divNode.appendChild(document.createElement("br")); }
            const spanNode = document.createElement("span");
            spanNode.innerHTML = "Speaker " + (currSpeaker + 1).toString() + ": ";
            spanNode.className = "transcript-speaker";
            divNode.appendChild(spanNode);
            prevSpeaker = currSpeaker;
          }
          if (entry[1].word !== "") {
            const spanNode = document.createElement("span");
            spanNode.innerHTML = entry[1].word;
            spanNode.className = entry[1].is_final ? "final" : "interim";
            divNode.appendChild(spanNode);
            divNode.appendChild(document.createTextNode(" "));
          }
        });
      var i = 0;
      console.log("entering loop");
      while (i < divNode.childNodes.length) {
        console.log(divNode.childNodes[i]);
        if (divNode.childNodes[i].className == "interim") {
          var j = i + 1;
          while (j < divNode.childNodes.length && (divNode.childNodes[j].nodeName == "#text" || divNode.childNodes[j].className == "interim")) {
            console.log(divNode.childNodes[j]);
            j++;
          }
          if (j < divNode.childNodes.length && divNode.childNodes[j].className == "final") {
            divNode.removeChild(divNode.childNodes[i]);
          } else { i++; }
        } else { i++; }
      }
      return divNode;
    }
  }

  /**
   * Retrieves the room ID and makes the socket
   * the corresponding room.
   *
   * @param {HTMLElement} shareNode
   * @param {SocketIOClient.Socket} socket
   */
  function initRoom(shareNode, socket) {
    /**
     * The room ID is specified in the path. We expect something like `/{roomId}`.
     *
     * In case there is no room ID in the URL, we generate a random one
     * and update the URL in the navigation bar (without adding
     * a new entry in the history).
     */
    const roomRequested = location.pathname.substring(1);
    const room = roomRequested == "" ? randomId() : roomRequested;
    window.history.replaceState(null, "Audio Chat", "/" + room);
    // window.history.replaceState(null, "Video Chat", "/" + room);
    shareNode.innerText = location + "";

    socket.emit("join", room);
    socket.on("full", (room) => {
      alert("Room " + room + " is full");
    });
  }

  /**
   * Modify the "Edit on Glitch" tag to point to the
   * Glitch editor.
   *
   * @param {HTMLAnchorElement} editOnGlitchNode
   */
  function initEditGlitch(editOnGlitchNode) {
    const [subdomain, ...domain] = location.host.split(".");
    if (domain.length === 2 && domain[0] === "glitch" && domain[1] === "me") {
      editOnGlitchNode.href = "https://glitch.com/edit/#!/" + subdomain;
    } else {
      editOnGlitchNode.remove();
    }
  }

  /**
   * @returns {string} */
  function randomId() {
    var characters =
      "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
    var result = "";
    for (var i = 0; i < 10; i++) {
      result += characters.charAt(
        Math.floor(Math.random() * characters.length)
      );
    }
    return result;
  }

  main();
})();
