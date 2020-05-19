/*
python.js -- what a name!

The interface between the frontend JS code and the "backend" (but still
in-browser) Python code (which is running through Pyodide / WASM). This
isn't functionally different from any other adapter that connects two pieces
of tech, but the name "python.js" is kind of wild.
*/

async function testPython() {
  pyodide.runPython(`
    import sys
    print(sys.version)
  `);
  pyodide.runPython("print(f'1 + 2 = {1 + 2}')")
};

async function importRescues() {
  // Load rescue module, try to create test code
  let rescues = await fetch("python/rescue.py", { mode: "no-cors" }).then(x => x.text());
  pyodide.runPython(rescues);
  pyodide.runPython(`
    code = RescueCode('Pf8sPs4fPhXe3f7h1h2h5s8w3h9s3fXh4wMw4s6w8w9w6e2f8h9f1h2s1w8h')
    print(code)
    print(code.decode())
  `);
};

function generateRevivalPassword(passwordSymbols) {
  // passwordSymbols: array of 30 2-char symbols
  // return: array of 30 2-char symbols

  revival = pyodide.runPython(`
    code = RescueCode("".join(passwordSymbols));
    revival = code.decode()
    revival
  `);

  console.log(revival);
  return revival;
}
