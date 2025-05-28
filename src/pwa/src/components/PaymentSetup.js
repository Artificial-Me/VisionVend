import React, { useState } from 'react';
import { CardElement, useStripe, useElements } from '@stripe/react-stripe-js';

const PaymentSetup = ({ onSuccess }) => {
  const stripe = useStripe();
  const elements = useElements();
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    if (!stripe || !elements) {
      setError('Stripe.js has not loaded yet.');
      setLoading(false);
      return;
    }
    const card = elements.getElement(CardElement);
    if (!card) {
      setError('Card element not found.');
      setLoading(false);
      return;
    }
    const { error: stripeError, paymentMethod } = await stripe.createPaymentMethod({
      type: 'card',
      card
    });
    if (stripeError) {
      setError(stripeError.message);
      setLoading(false);
      return;
    }
    try {
      const response = await fetch('/save-payment', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ paymentMethodId: paymentMethod.id })
      });
      if (!response.ok) {
        const data = await response.json();
        setError(data.message || 'Failed to save payment method.');
        setLoading(false);
        return;
      }
      onSuccess();
    } catch (err) {
      setError('Network error. Please try again.');
    }
    setLoading(false);
  };


  return (
    <div className="flex flex-col items-center justify-center h-screen p-4">
      <h1 className="text-2xl font-bold mb-4">Add Payment Method</h1>
      <form onSubmit={handleSubmit} className="w-80">
        <CardElement className="border p-2 mb-4 rounded" />
        <button
          className="bg-blue-500 text-white px-4 py-2 rounded-lg"
          type="submit"
          aria-label="Save Payment"
          disabled={loading}
        >
          {loading ? 'Saving...' : 'Save Payment'}
        </button>
        {error && <p className="text-red-500 mt-2">{error}</p>}
      </form>
    </div>
  );
};

export default PaymentSetup;
