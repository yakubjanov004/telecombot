export default function TypingIndicator({ visible }) {
  if (!visible) return null;

  return (
    <div className="typing-indicator" role="status" aria-label="Operator yozmoqda">
      <div className="typing-indicator__dots">
        <span /><span /><span />
      </div>
      <span className="typing-indicator__text">Operator yozmoqda</span>
    </div>
  );
}
