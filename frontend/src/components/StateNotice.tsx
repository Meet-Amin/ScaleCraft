interface StateNoticeProps {
  title: string;
  message: string;
  tone?: "neutral" | "loading" | "error";
}

export function StateNotice({ title, message, tone = "neutral" }: StateNoticeProps) {
  return (
    <div className={`state-notice state-notice-${tone}`}>
      <strong>{title}</strong>
      <p>{message}</p>
    </div>
  );
}
