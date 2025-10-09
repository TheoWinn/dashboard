# Setting up the Frontend

⚙️ Prerequisites

Before you begin, you'll need to install a few essential tools.

### 1. Node.js

Our project uses the Node.js runtime environment. Installing it will also give you npm, which we'll use to install pnpm.

Download: Go to the official Node.js website and download the LTS (Long-Term Support) version. (https://nodejs.org/en/download)

Install: Run the installer and follow the on-screen prompts. The default settings are fine.

Verify: Open a new Command Prompt or PowerShell and type node -v. You should see a version number, which confirms it's installed correctly.

### 2. pnpm (Performant npm)

We use pnpm as our package manager because it's fast and efficient at managing project dependencies.

Install: Once Node.js is installed, open a Command Prompt or PowerShell and run the following command to install pnpm globally on your system:

    npm install -g pnpm

Verify: Close and reopen your terminal, then type pnpm -v. You should see the pnpm version number.

### Getting Started

**(Assuming you have already cloned and navigated into the frontend/ directory)** <- THIS IS IMPORTANT

3. Install Project Dependencies
This command reads the package.json file and downloads all the required libraries into a node_modules folder.

    pnpm install

4. Run the Development Server
This will start a local web server.

    pnpm dev

**Once it's running, your terminal will show a local URL, usually http://localhost:5173/. Open this URL in your web browser to see the application. The server will automatically reload the page whenever you make changes to the code.**

### Frontend information
We are using Vite+React+Javascript

# These files are important:
- Index.html: The main HTML file we specify some website wide 
- src/App.jsx: Main application component
- src/assets: Folder for static assets like images and styles

# Best practive

 If we create something like a new component, we should create a new folder in src/components and put the component file there. For example, if we create a Button component, we should create a folder src/components/Button and put Button.jsx and Button.css (if needed) there.
 .css is for styling/visuals, .jsx is for the logic/structure of the component (e.g what happens on click)
 We then import these components into the main App.jsx or other components as needed.
 

 # Important to know
**"States"**
They are information that can change over time. For example, if we have a button that when clicked changes the text on the screen, we would use a state to keep track of the text. When the button is clicked, we update the state and React automatically updates the screen for us.
This is important because usually JS re-renders the whole page when something changes, but with states, React only updates the parts of the page that need to change, making it more efficient!! **We should definitely use states for api refreshs since they take long!**

**Props** Basically function arguments that are used in your component:

Example:
*function Greeting({ name }) return <hello,{name}>*)
Greeting name = "Leonie"
Greeting name = "Tim"
Greeting name = "Ara"
Greeting name = "Theo"


**Side Effects** is an action that happens outside of the component. For example, fetching data from an API or updating the document title. In React, we use the useEffect hook to handle side effects. It takes a function as an argument and runs it after the component renders. We can also specify dependencies so that the effect only runs when certain values change.

E.g change in state or prop -> refresh api
-> click button -> change state -> refresh api

**Conditional rendering**
Show only certain parts of the UI based on certain conditions. For example, we can show a loading spinner while data is being fetched and then show the data once it is available. We can use JavaScript's conditional operators (like if statements or ternary operators) to achieve this. Side Effects is an action that happens outside of the component. For example, fetching data from an API or updating the document title. In React, we use the useEffect hook to handle side effects. It takes a function as an argument and runs it after the component renders. We can also specify dependencies so that the effect only runs when certain values change.

**Props aka properties**
are a way to pass data from a parent component to a child component. They are read-only and cannot be modified by the child component. We use props to make components reusable and configurable. For example, we can create a Button component that takes a label prop to set the text on the button.

Example:



**Conditional rendering**
Show only certain parts of the UI based on certain conditions. For example, we can show a loading spinner while data is being fetched and then show the data once it is available. We can use JavaScript's conditional operators (like if statements or ternary operators) to achieve this.

Example:

is logged in? show profile : show login button

 # Connecting Python backend to frontend
 We use an API to connect the Python backend to the React frontend. The backend will have endpoints that the frontend can call to get or send data. For this we use Flask and CORS (Cross-Origin Resource Sharing) to allow the frontend to communicate with the backend (Usually this would be blocked).

 # General Workflow
 - Use Python to handle data scraping/api calling as well as data processing (e.g cleaning, transforming, etc) and then send this data to the frontend via an backend-frontend API.


 # Possible visualizations:
 https://recharts.org (simple+easy to use)
 www.chartjs.org/ (also simple+easy to use)
 https://d3js.org/ (apparently harder to use)

 # Use for "scrolly-telling" 
 - https://www.npmjs.com/package/react-intersection-observer

 # The Matching Algorithm (matching.py)
 We need to match transcribed speeches from video to the actual speeches from the BT api. For this we strip stopwords and capitalization and then create a tf-idf vectorizer which indexes the speeches. This means that we get a unqiue fingerprint for each speech. We then do the same for the transcribed speech and then calculate the cosine similarity between the transcribed speech and all the indexed speeches. The speech with the highest cosine similarity is then returned as the best match.