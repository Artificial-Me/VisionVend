import React, { useState } from 'react';
// import { Elements, CardElement, useStripe, useElements } from '@stripe/react-stripe-js';
// import { loadStripe } from '@stripe/stripe-js';

// const stripePromise = loadStripe('pk_test_your_publishable_key');

const PaymentSetup = ({ onSuccess }) => {
  // const stripe = useStripe();
  // const elements = useElements();
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    // const card = elements.getElement(CardElement);
    // const { error, paymentMethod } = await stripe.createPaymentMethod({
    //   type: 'card',
    //   card
    // });
    // if (error) {
    //   setError(error.message);
    // } else {
    //   await fetch('/save-payment', {
    //     method: 'POST',
    //     headers: { 'Content-Type': 'application/json' },
    //     body: JSON.stringify({ paymentMethodId: paymentMethod.id })
    //   });
    //   onSuccess();
    // }
    onSuccess();
  };

  return (
    <div className="flex flex-col items-center justify-center h-screen p-4">
      <h1 className="text-2xl font-bold mb-4">Add Payment Method</h1>
      <form onSubmit={handleSubmit} className="w-80">
        {/* <CardElement className="border p-2 mb-4 rounded" /> */}
        <input className="border p-2 mb-4 rounded w-full" placeholder="Card Number (demo)" />
        <button
          className="bg-blue-500 text-white px-4 py-2 rounded-lg"
          type="submit"
          aria-label="Save Payment"
        >
          Save Payment
        </button>
        {error && <p className="text-red-500 mt-2">{error}</p>}
      </form>
    </div>
  );
};

// export default () => (
//   <Elements stripe={stripePromise}>
//     <PaymentSetup />
//   </Elements>
// );
export default PaymentSetup;
