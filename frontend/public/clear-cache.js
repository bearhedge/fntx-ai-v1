// Clear all caches when loading the page
if ('caches' in window) {
  caches.keys().then(function(names) {
    for (let name of names)
      caches.delete(name);
  });
}

// Unregister any service workers
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.getRegistrations().then(function(registrations) {
    for(let registration of registrations) {
      registration.unregister();
    }
  });
}