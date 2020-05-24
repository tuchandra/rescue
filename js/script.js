var rescuePasswordInput;

window.onload = function () {
  rescuePasswordInput = document.getElementById("password-input");
  pyImportRescues();
};

async function pyImportRescues() {
  // Load rescue module, try to create test code
  let rescues = await fetch("python/rescue.py", { mode: "no-cors" }).then((x) =>
    x.text()
  );
  pyodide.runPython(rescues);
  pyodide.runPython(`
    password = rescue_password_from_text('Pf8sPs4fPhXe3f7h1h2h5s8w3h9s3fXh4wMw4s6w8w9w6e2f8h9f1h2s1w8h')
    rescue = RescueCode.from_password(password)
    print(rescue.to_text())
    revival = RevivalCode.from_rescue_code(rescue)
    print(revival, code_to_symbols(revival))
  `);
}

function pyValidateRescuePassword(passwordSymbols) {
  // Checks if an entered rescue password is valid
  // passwordSymbols: array of 30 2-char symbols
  // return: true or false

  // This is necessary for Python to see the JS object
  window.passwordSymbols = passwordSymbols;

  let valid = pyodide.runPython(`
    from js import passwordSymbols;

    code = rescue_password_from_text("".join(passwordSymbols))
    components = decode_rescue_password(code)
    components.validate()
  `)

  console.log("Checking valid: ", valid);
  return valid
}

function pyGenerateRevivalPassword(passwordSymbols) {
  // passwordSymbols: array of 30 2-char symbols
  // return: array of 30 2-char symbols

  // This is necessary for Python to see the JS object
  window.passwordSymbols = passwordSymbols;

  revival = pyodide.runPython(`
    from js import passwordSymbols;

    code = rescue_password_from_text("".join(passwordSymbols))
    print(components.to_text())
    print(components.validate())

    get_revival_from_rescue(components)
  `);

  console.log(revival);
  return revival;
}

function pyGenerateRescuePassword(dungeon, floor, team) {
  // Generate a rescue password given dungeon, floor, and team

  window.dungeon = dungeon
  window.floor = floor
  window.team = team

  let rescue = pyodide.runPython(`
    from js import dungeon, floor, team

    rescue = RescueCode.from_scratch(dungeon_name=dungeon, floor=floor, team_name=team)
    print(rescue.to_text())

    if not rescue.validate():
      raise ValueError("rescue info invalid -- probably from floor being impossible")

    symbols = code_to_symbols(rescue)
    print("".join(symbols))
    symbols
  `)

  return rescue;
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

const fillPassword = function (field, symbols) {
  // Fill the password output with a provided set of text symbols

  var i = 0;
  for (group of field.children) {
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

  // Check if valid
  let text = symbolsToText(passwordSymbols);
  if (pyValidateRescuePassword(text) === false) {
    // Password is incomplete
    invalidPasswordMessage = document.getElementById("password-invalid");
    invalidPasswordMessage.classList.remove("hidden");

    return;
  }

  invalidPasswordMessage = document.getElementById("password-invalid");
  invalidPasswordMessage.classList.add("hidden");

  // If we reached this point, the password is valid - generate revival and call it a day
  let revivalPassword = pyGenerateRevivalPassword(text);
  console.log("revivalPassword: ", revivalPassword);

  // Put revival password in the space
  let revivalPasswordOutput = document.getElementById("password-output");
  fillRevivalPassword(revivalPasswordOutput, revivalPassword);

  // Remove display:none
  document.getElementById("revival-password-text").classList.remove("hidden");
  revivalPasswordOutput.classList.remove("hidden");
};

const populateDungeons = function () {
  // Populate the dungeons dropdown menu
  // .
}

const submitRescueInfo = function () {
  // Submit info to generate a rescue
  document.getElementById("choose-a-floor").classList.add("hidden");
  document.getElementById("floor-invalid").classList.add("hidden");

  let dungeon = document.getElementById("rescue-dungeon").selectedOptions[0].value;
  let floor = document.getElementById("rescue-floor").value;
  let team = document.getElementById("rescue-team").value;

  if (floor === "") {
    document.getElementById("choose-a-floor").classList.remove("hidden");
    return;
  }

  team = (team === "") ? "tusharc.dev" : team

  // Get the rescue code, fill it in
  let rescuePassword;
  try {
    rescuePassword = pyGenerateRescuePassword(dungeon, parseInt(floor), team);
  } catch {
    // The password was invalid, probably because of floor being out of range
    document.getElementById("floor-invalid").classList.remove("hidden");
    document.getElementById("generated-password").classList.add("hidden");
    document.getElementById("rescue-password-text").classList.add("hidden");
    return;
  }

  let passwordField = document.getElementById("generated-password");
  fillPassword(passwordField, rescuePassword);

  passwordField.classList.remove("hidden");
  document.getElementById("rescue-password-text").classList.remove("hidden");
  return;
}


const getDummyPasswordSymbols = function () {
  // Helper to just get some dummy symbols at any time

  return [
    "1F",
    "2F",
    "3F",
    "4F",
    "5F",
    "1E",
    "2E",
    "3E",
    "4E",
    "5E",
    "1S",
    "2S",
    "3S",
    "4S",
    "5S",
    "1W",
    "2W",
    "3W",
    "4W",
    "5W",
    "1H",
    "2H",
    "3H",
    "4H",
    "5H",
    "PS",
    "XH",
    "XE",
    "XW",
    "XF",
  ]
}