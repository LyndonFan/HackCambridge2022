const buttonForHelp = document.getElementById("helpButton");

const callForHelp = async (event) => {
    const person = "your uncle Bob";
    const text = "I need help! I'm in a terrible pain!";
    const response = await fetch("/call-for-help", {
        method: "POST",
        headers: {
            Accept: "application/json",
            "Content-Type": "application/json",
        },
        body: JSON.stringify({ person: person, text: text }),
    });
    console.log(response);
};

buttonForHelp.addEventListener("click", callForHelp);