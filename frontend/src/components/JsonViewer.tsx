import { prettyJson } from "../utils/formatters";

interface JsonViewerProps {
  value: unknown;
}

export function JsonViewer({ value }: JsonViewerProps) {
  return <pre className="code-block">{prettyJson(value)}</pre>;
}
