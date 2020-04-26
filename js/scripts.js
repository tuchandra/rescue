const initialize = async function () {
  $(document).trigger("input");
  await initializePython();
}


// NEW NEW NEW NEW NEW
const rescueCodeInput = document.getElementsByClassName("password-input")[0];
const revivalPasswordOutput = document.getElementsByClassName("password-output")[0];

const addToCode = function(element) {
  newElement = element.cloneNode(true);
  newElement.setAttribute("onclick", "removeFromPassword(this)");
  replacePlaceholderSymbol(newElement);

  // Remove the invalid style from the symbols
  for (group of rescueCodeInput.children) {
    for (space of group.children) {
      if (space.classList.contains("rescue-invalid")) {
        space.classList.remove("rescue-invalid");
      }
    }
  }

  // Remove invalid message
  tooShortMessage = document.getElementById("password-too-short");
  tooShortMessage.setAttribute("style", "display:none");
}

const replacePlaceholderSymbol = function(element) {
  // Find the first empty space in the rescue code input; put element in it
  for (group of rescueCodeInput.children) {
    for (space of group.children) {
      if (space.classList.contains("rescue-placeholder")) {
        space.replaceWith(element);
        return;
      }
    }
  }
}

const getBackgroundName = function(char) {
  // Convert char "h" -> background name "heart" etc.
  if (char === "f") {
    return "fire";
  } else if (char === "h") {
    return "heart";
  } else  if (char === "w") {
    return "water";
  } else if (char === "e") {
    return "emerald";
  } else if (char === "s") {
    return "star";
  }

  throw new Error("invalid background symbol, must be f / h / w / e / s")
}

const textToSymbol = function(text) {
  // Convert text 4e, Xw, etc. to rescue symbol HTML element
  let label = text[0];
  let background = getBackgroundName(text[1]);

  let newElement = document.createElement("button");
  newElement.classList.add("rescue-symbol");
  newElement.setAttribute("background", background);
  newElement.setAttribute("label", label);
  newElement.textContent = label;

  return newElement;
}

const fillPlaceholderOutput = function(symbols) {
  // Fill the password output with a provided set of text symbols

  var i = 0;
  for (group of revivalPasswordOutput.children) {
    for (space of group.children) {
      space.replaceWith(textToSymbol(symbols[i]));
      i++;
    }
  }

}

const removeFromPassword = function(element) {
  element.classList.replace("rescue-symbol", "rescue-placeholder");
  element.removeAttribute("background");
  element.removeAttribute("label");
  element.textContent = "\xa0";
}

const getEnteredSymbols = function() {
  // Get the symbols that the user entered
  // Throw error if it's incomplete, but do not do any additional validation
  // (that part gets offloaded to Python)

  let symbols = new Array();
  for (group of rescueCodeInput.children) {
    for (symbol of group.children) {
      if (symbol.classList.contains("rescue-placeholder")) {
        throw Error("Password is incomplete!");
      }

      symbols.push(symbol);
    }
  }

  return symbols;
}

const symbolsToText = function(symbols) {
  // Convert HTML collection of rescue symbols to the text represented by each,
  // e.g., 4e 5s Xf ...

  return [
    "1f", "2f", "3f", "4f", "5f",
    "1e", "2e", "3e", "4e", "5e",
    "1s", "2s", "3s", "4s", "5s",
    "1w", "2w", "3w", "4w", "5w",
    "1h", "2h", "3h", "4h", "5h",
    "Xs", "Xh", "Xe", "Xw", "Xf",
  ]

  let text = new Array();
  for (symbol of symbols) {
    let label = symbol.getAttribute("label")[0];
    let background = symbol.getAttribute("background")[0];
    text.push(label.toUpperCase() + background);
  }

  return text;
}

const pyGenerateRevivalPassword = function(text) {
  // Interface into Python function to generate a revival password
  return text;
}

const submitPassword = function() {
  // Submit an entered password for decoding - send to Pyodide to validate
  try {
    var passwordSymbols = getEnteredSymbols();
  } catch {
    // Password is incomplete
    tooShortMessage = document.getElementById("password-too-short");
    tooShortMessage.setAttribute("style", "");

    // Highlight the empty symbols in the entered password
    for (group of rescueCodeInput.children) {
      for (space of group.children) {
        if (space.classList.contains("rescue-placeholder")) {
          space.classList.add("rescue-invalid");
        }
      }
    }

    return;
  }



  // Send password to Python
  // TODO: actually do this; for now it returns a default password
  let text = symbolsToText(passwordSymbols);
  try {
    var revivalPassword = pyGenerateRevivalPassword(text);
    console.log("revivalPassword: ", revivalPassword);
  } catch {
    // Password was invalid ... do something
    console.log("password invalid ...");
  }

  // Put revival password in the space
  fillPlaceholderOutput(revivalPassword);

  // Remove display:none
  document.getElementById("revival-password-text").setAttribute("style", "");
  document.getElementsByClassName("password-output")[0].setAttribute("style", "");

}
