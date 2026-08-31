import { Link } from "react-router-dom";

export function Brand() {
  return (
    <Link className="inline-flex items-center text-xl font-bold tracking-tight text-white" to="/">
      Dark<span className="text-brand-400">Audit</span>
    </Link>
  );
}
