// frontend/src/App.jsx

import { useState, useEffect } from 'react';
import MyChart from './components/MyChart'; // -> 1. IMPORT your new component

function App() {
  const [data, setData] = useState(null);

  useEffect(() => {
    fetch('http://127.0.0.1:5000/api/data')
      .then(response => response.json())
      .then(data => setData(data))
      .catch(error => console.error("There was an error!", error));
  }, []);

  return (
    <div>
      <h1>Data from Flask Backend</h1>
      {data ? (
        <div>
          {/* This section shows the data from your backend */}
          <p><strong>Message:</strong> {data.message}</p>
          <ul>
            {data.items.map((item, index) => (
              <li key={index}>{item}</li>
            ))}
          </ul>

          <hr /> {/* Adding a line to separate the sections */}

          <h2>Sales Chart</h2>
          {/* -> 2. ADD the new component's tag here */}
          <MyChart />
        </div>
      ) : (
        <p>Loading data...</p>
      )}
    </div>
  );
}

export default App;