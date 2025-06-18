# Domain Setup for Google OAuth

Google OAuth requires a proper domain name, not an IP address. Here's how to set it up:

## Using nip.io (Quickest Solution)

1. Your domain will be: `http://35-194-231-94.nip.io:8080`
2. In Google Cloud Console, add this to Authorized JavaScript origins
3. Access your app via this URL instead of the IP

## In Google Cloud Console:

1. Go to APIs & Services > Credentials
2. Click on your OAuth 2.0 Client ID
3. Under "Authorized JavaScript origins", add:
   - `http://35-194-231-94.nip.io:8080`
   - `http://localhost:8080` (for local development)
4. Under "Authorized redirect URIs", add the same URLs
5. Save

## Update Your App:

No code changes needed! Just access your app using:
```
http://35-194-231-94.nip.io:8080
```

Instead of:
```
http://35.194.231.94:8080
```

## How nip.io Works:

- `35-194-231-94.nip.io` automatically resolves to `35.194.231.94`
- Google accepts it because it ends with `.io`
- No registration or setup required

## Alternative: Get a Real Domain

For production, consider:
1. Buy a domain from Namecheap, GoDaddy, etc. (~$10/year)
2. Point it to your server IP
3. Use that domain in Google OAuth settings