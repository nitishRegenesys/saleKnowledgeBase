import { useEffect, useState } from "react";

/**
 * Minimal hash router.
 *
 * The production build is served by FastAPI's StaticFiles mount, which has no
 * SPA fallback, so a path-based route (`/calls`) would 404 on refresh. Hash
 * routes always resolve to index.html, which keeps this dependency-free.
 *
 *   #/        -> home (Chat | AI Calling chooser)
 *   #/chat    -> chat
 *   #/calls   -> AI calling dashboard
 */

const KNOWN_PREFIXES = ["/chat", "/calls"];

function readRoute() {
  const hash = window.location.hash.replace(/^#/, "");

  if (!hash || hash === "/") {
    return "/";
  }

  return KNOWN_PREFIXES.some((prefix) => hash.startsWith(prefix))
    ? hash
    : "/";
}

export default function useHashRoute() {
  const [route, setRoute] = useState(readRoute);

  useEffect(() => {
    function handleHashChange() {
      setRoute(readRoute());
    }

    window.addEventListener("hashchange", handleHashChange);

    return () =>
      window.removeEventListener("hashchange", handleHashChange);
  }, []);

  function navigate(nextRoute) {
    if (readRoute() === nextRoute) {
      return;
    }

    window.location.hash = nextRoute;
  }

  return { route, navigate };
}
