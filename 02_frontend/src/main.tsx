import { createRoot } from 'react-dom/client'
import App from './App.tsx'
import './index.css'

console.log('main.tsx: Starting React app');

const rootElement = document.getElementById("root");
console.log('main.tsx: Root element found:', !!rootElement);

if (!rootElement) {
  console.error('main.tsx: Root element not found!');
  document.body.innerHTML = '<h1>Error: Root element not found</h1>';
} else {
  try {
    console.log('main.tsx: Creating React root');
    const root = createRoot(rootElement);
    console.log('main.tsx: Rendering App component');
    root.render(<App />);
    console.log('main.tsx: App component rendered successfully');
  } catch (error) {
    console.error('main.tsx: Error rendering app:', error);
    rootElement.innerHTML = '<h1>Error rendering React app: ' + error.message + '</h1>';
  }
}
