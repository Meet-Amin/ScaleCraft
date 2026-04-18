import { useState } from "react";

import { HomePage } from "./pages/HomePage";

const DEFAULT_PROMPT =
  "Build a global ecommerce marketplace where shoppers browse products, search inventory, checkout with Stripe, receive notifications, and the platform must handle 500 rps baseline, 3000 rps peak, and 8000 concurrent users with 99.95% availability.";

export default function App() {
  const [requirementText, setRequirementText] = useState<string>(DEFAULT_PROMPT);

  return <HomePage requirementText={requirementText} onRequirementTextChange={setRequirementText} />;
}
