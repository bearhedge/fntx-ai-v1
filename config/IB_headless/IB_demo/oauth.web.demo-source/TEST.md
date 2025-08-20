# Automated testing for CP Gateway

## Adding endpoint to test

Open test.html with a text editor.  Look for "var endpoints".  To add an endpoint to be tested, add the following after the last curly brace:
```
{url: 'ENDPOINT', method: 'METHOD'},
```
If the endpoint you want to test requires a body, e.g. POST endpoints, add the following:
```
{url: 'ENDPOINT', method: 'METHOD', body: { BODY_CONTENTS }},
```
### Example endpoints
```
{url: '/portal/sso/validate', method: 'GET'},

{url: '/fake/endpoint', method: 'POST', body: { test: 'hello' }},
```
## Running automated test

Make sure you have the CP gateway open and running, and have logged in.  Simply press "Test Endpoints" button and test results will show.
