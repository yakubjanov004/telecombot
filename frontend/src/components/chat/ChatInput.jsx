import { useEffect, useRef } from 'react';
import Button from '../ui/Button';

export default function ChatInput({
  value,
  onChange,
  onSend,
  onImageUpload,
  disabled,
  uploading,
  cooldownSec,
  isCooldown,
  focusToken,
}) {
  const fileRef = useRef(null);
  const inputRef = useRef(null);

  const focusInput = () => {
    window.requestAnimationFrame(() => {
      if (!disabled) inputRef.current?.focus();
    });
  };

  useEffect(() => {
    focusInput();
  }, [disabled, focusToken]);

  const handleSubmit = (e) => {
    e.preventDefault();
    const sent = onSend?.();
    if (sent !== false) focusInput();
  };

  return (
    <form className="chat-input" onSubmit={handleSubmit}>
      <div className="chat-input__inner">
        <button
          type="button"
          className="chat-input__attach"
          onClick={() => fileRef.current?.click()}
          disabled={disabled || uploading || isCooldown}
          aria-label="Rasm yuklash"
        >
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>
        <input
          ref={fileRef}
          type="file"
          accept="image/*"
          hidden
          onChange={onImageUpload}
        />
        <input
          ref={inputRef}
          type="text"
          className="chat-input__field"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={isCooldown ? `Kuting (${cooldownSec}s)...` : 'Xabar yozing...'}
          disabled={disabled}
          aria-label="Xabar matni"
        />
        <Button
          type="submit"
          variant="primary"
          size="sm"
          disabled={!value.trim() || disabled || isCooldown}
          aria-label="Yuborish"
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </Button>
      </div>
    </form>
  );
}
