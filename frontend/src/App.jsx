import { useState } from "react";
import Landing from "./pages/Landing.jsx";
import Topic from "./pages/Topic.jsx";

export default function App() {
  const [selectedSlug, setSelectedSlug] = useState(null);

  if (selectedSlug) {
    return (
      <Topic
        slug={selectedSlug}
        onBack={() => setSelectedSlug(null)}
        onSelectTopic={(slug) => setSelectedSlug(slug)}
      />
    );
  }

  return <Landing onSelectTopic={(slug) => setSelectedSlug(slug)} />;
}
