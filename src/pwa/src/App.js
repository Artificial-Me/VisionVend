import React, { useState, useEffect } from 'react';
import Home from './components/Home';
import SignIn from './components/SignIn';
import PaymentSetup from './components/PaymentSetup';
import Unlocking from './components/Unlocking';
import Transaction from './components/Transaction';
import Receipt from './components/Receipt';
// import { useAuth } from './hooks/useAuth';
// import { NDEFReader } from './utils/nfc';

const mockAuth = { user: null, isAuthenticated: false }; // Replace with real auth

const App = () => {
  const { user, isAuthenticated } = mockAuth; // Replace with useAuth()
  const [screen, setScreen] = useState('home');
  const [transaction, setTransaction] = useState({ id: '', items: [], total: 0 });

  useEffect(() => {
    // NFC/QR logic placeholder
    // if ('NDEFReader' in window) {
    //   const reader = new NDEFReader();
    //   reader.scan().then(() => {
    //     reader.onreading = () => {
    //       if (isAuthenticated) {
    //         setScreen('unlocking');
    //         unlock();
    //       } else {
    //         setScreen('signin');
    //       }
    //     };
    //   });
    // }
  }, [isAuthenticated]);

  const unlock = async () => {
    try {
      // Replace with real endpoint
      const response = await fetch('/unlock', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: Date.now().toString(16) })
      });
      const data = await response.json();
      if (data.status === 'success') {
        setScreen('transaction');
        setTransaction({ id: data.transaction_id, items: [], total: 0 });
      } else {
        setScreen('home');
        alert('Error: ' + data.message);
      }
    } catch (e) {
      setScreen('home');
      alert('Network error, please try again');
    }
  };

  const handleReceipt = (data) => {
    setTransaction({ ...transaction, items: data.items, total: data.total });
    setScreen('receipt');
  };

  return (
    <div className="min-h-screen bg-white">
      {screen === 'home' && <Home onQRScan={unlock} />}
      {screen === 'signin' && <SignIn onSuccess={() => setScreen('payment')} />}
      {screen === 'payment' && <PaymentSetup onSuccess={() => setScreen('home')} />}
      {screen === 'unlocking' && <Unlocking />}
      {screen === 'transaction' && <Transaction transaction={transaction} />}
      {screen === 'receipt' && <Receipt transaction={transaction} />}
    </div>
  );
};

export default App;
