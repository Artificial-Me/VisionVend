import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import './styles/tailwind.css';
import { Elements } from '@stripe/react-stripe-js';
import { loadStripe } from '@stripe/stripe-js';

const stripePromise = loadStripe('pk_live_51RIxuqE8x3DSMv9qDrEf6Yx1KbJ5RFb4TNh46TgKHWaOQMyTELWrH4vKHIxyrAG7GUsfoScfW2b6CnvLxAMjDJvr008AGOcdo9');

createRoot(document.getElementById('root')).render(
  <Elements stripe={stripePromise}>
    <App />
  </Elements>
);

if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js');
  });
}
