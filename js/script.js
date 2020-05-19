// import * as python from "./python.js";

var rescuePasswordInput;
var revivalPasswordOutput;

window.onload = function () {
  rescuePasswordInput = document.getElementById("password-input");
  revivalPasswordOutput = document.getElementById("password-output");
  pyImportRescues();
};

async function pyImportRescues() {
  // Load rescue module, try to create test code
  let rescues = await fetch("python/rescue.py", { mode: "no-cors" }).then((x) =>
    x.text()
  );
  pyodide.runPython(rescues);
  pyodide.runPython(`
    code = RescueCode('Pf8sPs4fPhXe3f7h1h2h5s8w3h9s3fXh4wMw4s6w8w9w6e2f8h9f1h2s1w8h')
    print(code)
  `);
}

function pyGenerateRevivalPassword(passwordSymbols) {
  // passwordSymbols: array of 30 2-char symbols
  // return: array of 30 2-char symbols

  window.passwordSymbols = passwordSymbols;

  revival = pyodide.runPython(`
    # This is necessary for Python to see the JS object
    from js import passwordSymbols;

    code = RescueCode("".join(passwordSymbols))
    revival = code.decode()
    revival
  `);

  console.log(revival);
  return revival;
}

const addToPassword = function (element) {
  newElement = element.cloneNode(true);
  newElement.setAttribute("onclick", "removeFromPassword(this)");
  replaceFirstPlaceholder(newElement);

  // Remove any invalid style from the symbols
  for (group of rescuePasswordInput.children) {
    for (space of group.children) {
      // does nothing if the class is not present
      space.classList.remove("bg-red-300");
    }
  }

  // Remove invalid message
  tooShortMessage = document.getElementById("password-too-short");
  tooShortMessage.classList.add("hidden");
};

const removeFromPassword = function (element) {
  // Replace symbol with a placeholder
  element.classList = ["symbol rescue-placeholder"];
  element.textContent = "\xa0";
};

const replaceFirstPlaceholder = function (element) {
  // Find the first empty space in the rescue code input; put element in it
  for (group of rescuePasswordInput.children) {
    for (space of group.children) {
      if (space.classList.contains("rescue-placeholder")) {
        space.replaceWith(element);
        return;
      }
    }
  }
};

const getBackgroundName = function (char) {
  // Convert char "h" -> background name "heart" etc.
  char = char.toLowerCase();

  if (char === "f") {
    return "fire";
  } else if (char === "h") {
    return "heart";
  } else if (char === "w") {
    return "water";
  } else if (char === "e") {
    return "emerald";
  } else if (char === "s") {
    return "star";
  }

  throw new Error("invalid background symbol, must be f / h / w / e / s");
};

const textToSymbol = function (text) {
  // Convert text 4e, Xw, etc. to rescue symbol HTML element
  let label = text[0];
  let background = getBackgroundName(text[1]);

  let newElement = document.createElement("button");
  newElement.classList.add("symbol");
  newElement.classList.add("symbol-" + background);
  newElement.classList.add("cursor-default");
  newElement.textContent = label;

  return newElement;
};

const fillRevivalPassword = function (symbols) {
  // Fill the password output with a provided set of text symbols

  var i = 0;
  for (group of revivalPasswordOutput.children) {
    for (space of group.children) {
      space.replaceWith(textToSymbol(symbols[i]));
      i++;
    }
  }
};

const getEnteredSymbols = function () {
  // Get the symbols that the user entered
  // Throw error if it's incomplete, but do not do any additional validation
  // (that part gets offloaded to Python)

  let symbols = new Array();
  for (group of rescuePasswordInput.children) {
    for (symbol of group.children) {
      if (symbol.classList.contains("rescue-placeholder")) {
        throw Error("Password is incomplete!");
      }

      symbols.push(symbol);
    }
  }

  return symbols;
};

const symbolsToText = function (symbols) {
  // Convert HTML collection of rescue symbols to the text represented by each,
  // e.g., 4E 5S XF ...

  let text = new Array();
  for (symbol of symbols) {
    let label = symbol.innerText;

    // turn symbol-heart into H, symbol-water into W, etc., this one is the second class
    let background = symbol.classList[1].split("-")[1][0].toUpperCase();
    text.push(label.toUpperCase() + background);
  }

  return text;
};

const submitPassword = function () {
  // Submit an entered password for decoding - send to Pyodide to validate
  try {
    var passwordSymbols = getEnteredSymbols();
  } catch {
    // Password is incomplete
    tooShortMessage = document.getElementById("password-too-short");
    tooShortMessage.classList.remove("hidden");

    // Highlight the empty symbols in the entered password
    for (group of rescuePasswordInput.children) {
      for (space of group.children) {
        if (space.classList.contains("rescue-placeholder")) {
          space.classList.add("bg-red-300");
        }
      }
    }

    return;
  }

  // Send password to Python
  let text = symbolsToText(passwordSymbols);
  try {
    var revivalPassword = pyGenerateRevivalPassword(text);
    console.log("revivalPassword: ", revivalPassword);
  } catch {
    // Password was invalid ... do something
    console.log("password invalid ...");
  }

  // Put revival password in the space
  fillRevivalPassword(revivalPassword);

  // Remove display:none
  document.getElementById("revival-password-text").classList.remove("hidden");
  revivalPasswordOutput.classList.remove("hidden");
};
