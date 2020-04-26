/*
python.js -- what a name!

The interface between the frontend JS code and the "backend" (but still
in-browser) Python code (which is running through Pyodide / WASM). This
isn't functionally different from any other adapter that connects two pieces
of tech, but the name "python.js" is kind of wild.
*/

async function startPython() {
  console.log("Starting Python ...");
  await languagePluginLoader;

}

async function testPython() {
	pyodide.runPython(`
		import sys
		print(sys.version)
	`);
	pyodide.runPython("print(f'1 + 2 = {1 + 2}')");
};

async function importRescues() {
	// Load rescue module, try to create test code
	let rescues = await fetch("rescues/rescue.py", {mode: "no-cors"})
	let rescues_txt = await rescues.text();
	console.log(rescues_txt);
	pyodide.runPython(rescues_txt);
	console.log("Imported rescues/rescue.py!");

	console.log("Attempting to make rescue code ...")
	pyodide.runPython(`
		code = RescueCode.from_text('Pf8sPs4fPhXe3f7h1h2h5s8w3h9s3fXh4wMw4s6w8w9w6e2f8h9f1h2s1w8h')
		print(code)
	`);
};

async function initializePython() {
	await startPython();
	await testPython();
	await importRescues();
};
