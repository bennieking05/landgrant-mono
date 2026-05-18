import { Navigate, useLocation } from "react-router-dom";
import { useAppContext } from "@/context";
import { personaNavMap } from "@/constants/personaNav";

type Props = {
  path: string;
  children: React.ReactNode;
};

export function PersonaRoute({ path, children }: Props) {
  const { persona } = useAppContext();
  const location = useLocation();
  const allowed = personaNavMap[persona];
  const normalized = path.replace(/\/+$/, "") || "/";

  if (!allowed.includes(normalized)) {
    return (
      <Navigate
        to="/"
        replace
        state={{ from: location.pathname, reason: "persona" }}
      />
    );
  }

  return <>{children}</>;
}
