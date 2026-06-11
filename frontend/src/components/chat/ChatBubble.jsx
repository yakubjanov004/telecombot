import { formatTime } from '../../utils/format';

export default function ChatBubble({ message, onImageClick }) {
  const { sender, message: text, media_url, created_at, status } = message;
  const isClient = sender === 'client';
  const isSystem = sender === 'system';

  const imageUrl = media_url
    ? (media_url.startsWith('http') ? media_url : `/api${media_url}`)
    : null;

  if (isSystem) {
    return (
      <div className="chat-bubble chat-bubble--system" role="status">
        <span>{text}</span>
      </div>
    );
  }

  return (
    <div className={`chat-bubble chat-bubble--${sender}`}>
      <div className="chat-bubble__content">
        {imageUrl && (
          <button
            type="button"
            className="chat-bubble__image-btn"
            onClick={() => onImageClick?.(imageUrl)}
          >
            <img src={imageUrl} alt="Yuklangan rasm" loading="lazy" />
          </button>
        )}
        {text && <p className="chat-bubble__text">{text}</p>}
      </div>
      <div className="chat-bubble__meta">
        <time dateTime={created_at}>{formatTime(created_at)}</time>
        {isClient && status && (
          <span className={`chat-bubble__status chat-bubble__status--${status}`} aria-label={status}>
            {status === 'delivered' ? '✓✓' : '✓'}
          </span>
        )}
      </div>
    </div>
  );
}
