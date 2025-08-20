# IBKR WebAPI OAuth Demo

## Pre-requisites

NodeJS (latest version): https://nodejs.org/

A browser with CORS disabled must be used if running locally. For Chrome, use the --disable-web-security option along with the --user-data-dir option.

Example:

`"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" --disable-web-security --user-data-dir="J:"`

## Running the Demo

If all you want is try the demo, you can skip how to build demo section and go to the oauth demo section below.

### Building the Demo

Run "npm install" in oauth.demo directory to install all dependencies

Run "npm run dist" to build the demo. The files are generated to ./dist folder.  

Run "npm run demo" if you want to run the demo inside webpack dev server, do this if you are a developer and you want to play with the source code. The demo will be available under http://localhost:20000.


### OAuth Demo
 
Open the index.html inside ./dist

1. Press the Get Request Token button
2. Goto https://www.interactivebrokers.com/authorize?oauth_token=XXXXXX with cookies enabled
	2.1 Replace XXXXXX with the value in the Request Token field
3. Login with paper account and sign the form
4. You will be redirected to an empty page.  Copy the "oauth_verifier" field in the URL to the Verifier Token field
5. Turn cookies back off and press the Get Access Token & LST button
6. Press the Login button to access order form, positions and orders tables
