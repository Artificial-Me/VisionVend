import React, { useState } from 'react';
// import { signInWithGoogle, signInWithApple, signInWithEmail } from '../utils/auth';

const SignIn = ({ onSuccess }) => {
  const [email, setEmail] = useState('');

  const handleEmail = async () => {
    // await signInWithEmail(email);
    onSuccess();
  };

  return (
    <div className="flex flex-col items-center justify-center h-screen p-4">
      <h1 className="text-2xl font-bold mb-4">Sign In</h1>
      <input
        type="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        placeholder="Email"
        className="border p-2 mb-4 w-80 rounded"
        aria-label="Email address"
      />
      <button
        className="bg-blue-500 text-white px-4 py-2 rounded-lg mb-2"
        onClick={handleEmail}
        aria-label="Continue with Email"
      >
        Continue
      </button>
      <button
        className="bg-black text-white px-4 py-2 rounded-lg mb-2"
        // onClick={signInWithGoogle}
        aria-label="Sign in with Google"
      >
        Sign in with Google
      </button>
      <button
        className="bg-black text-white px-4 py-2 rounded-lg"
        // onClick={signInWithApple}
        aria-label="Sign in with Apple"
      >
        Sign in with Apple
      </button>
      <a href="/privacy" className="text-blue-500 text-sm mt-4">Privacy Policy</a>
    </div>
  );
};

export default SignIn;
