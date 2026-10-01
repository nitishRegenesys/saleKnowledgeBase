import ChatView from "./views/ChatView";
import CallingView from "./views/CallingView";
import HomeView from "./views/HomeView";

import useHashRoute from "./hooks/useHashRoute";

/**
 * Route shell. Home offers Chat or AI Calling; the two views can always go
 * back to it. Routing is hash-based (see useHashRoute) because the backend
 * serves the build through StaticFiles without an SPA fallback.
 */
function App() {
  const { route, navigate } = useHashRoute();

  if (route.startsWith("/chat")) {
    return (
      <ChatView onNavigateHome={() => navigate("/")} />
    );
  }

  if (route.startsWith("/calls")) {
    return (
      <CallingView onNavigateHome={() => navigate("/")} />
    );
  }

  return <HomeView onNavigate={navigate} />;
}

export default App;
