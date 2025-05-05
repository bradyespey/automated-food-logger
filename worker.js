//worker.js


addEventListener('fetch', event => {
    event.respondWith(handleRequest(event.request));
  });
  
  async function handleRequest(request) {
    const url = new URL(request.url);
  
    // Heroku backend
    const productionFoodLogHost = 'foodlogging-459c6f270ab7.herokuapp.com';
  
    if (url.pathname.startsWith('/foodlog')) {
      url.hostname = productionFoodLogHost;
  
      // Forward original Host and Proto headers
      const originalHost = request.headers.get('Host');
      const originalProto = request.headers.get('X-Forwarded-Proto') || 'https';
  
      const headers = new Headers(request.headers);
      headers.set('Host', productionFoodLogHost);
      headers.set('X-Forwarded-Host', originalHost);
      headers.set('X-Forwarded-Proto', originalProto);
  
      // Fetch from Heroku
      const response = await fetch(url.toString(), {
        method: request.method,
        headers,
        body: request.body,
        redirect: 'manual',
      });
  
      // Clone the response so we can manipulate headers
      let newResponse = new Response(response.body, response);
  
      // Copy Set-Cookie if present
      const setCookie = response.headers.get('Set-Cookie');
      if (setCookie) {
        newResponse.headers.set('Set-Cookie', setCookie);
      }
  
      return newResponse;
    }
  
    // Otherwise, return 404 Not Found
    return new Response('Not Found', { status: 404 });
  }