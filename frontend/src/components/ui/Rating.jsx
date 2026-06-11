import { useState } from 'react';

export default function Rating({ onRate, label = 'Xizmatni baholang' }) {
  const [hovered, setHovered] = useState(0);
  const [selected, setSelected] = useState(0);

  const handleClick = (value) => {
    setSelected(value);
    onRate?.(value);
  };

  return (
    <div className="rating" role="group" aria-label={label}>
      <p className="rating__label">{label}</p>
      <div className="rating__stars">
        {[1, 2, 3, 4, 5].map((star) => (
          <button
            key={star}
            type="button"
            className={`rating__star ${star <= (hovered || selected) ? 'active' : ''}`}
            onMouseEnter={() => setHovered(star)}
            onMouseLeave={() => setHovered(0)}
            onClick={() => handleClick(star)}
            aria-label={`${star} yulduz`}
          >
            ★
          </button>
        ))}
      </div>
      {selected > 0 && (
        <p className="rating__thanks">Rahmat! Siz {selected} yulduz berdingiz.</p>
      )}
    </div>
  );
}
