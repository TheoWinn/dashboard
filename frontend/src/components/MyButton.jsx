// src/components/MyButton.jsx

import { useState } from 'react';
import './MyButton.css'; // You can import CSS for styling

function MyButton() {
  // Functionality (JavaScript logic)
  const [count, setCount] = useState(0);

  function handleClick() {
    setCount(count + 1);
    console.log("Button was clicked!");
  }

  // Visuals (JSX that looks like HTML)
  return (
    <button onClick={handleClick}>
      Clicked {count} times
    </button>
  );
}

export default MyButton;

