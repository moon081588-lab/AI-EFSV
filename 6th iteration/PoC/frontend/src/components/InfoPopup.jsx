import React from 'react';
import { HelpCircle } from 'lucide-react';

export default function InfoPopup({ title, content }) {
  const [isOpen, setIsOpen] = React.useState(false);

  return (
    <span className="info-popup-wrap">
      <button
        className="info-popup-button"
        type="button"
        aria-label={`Explain ${title}`}
        onClick={(event) => {
          event.stopPropagation();
          setIsOpen((current) => !current);
        }}
      >
        <HelpCircle size={15} />
      </button>
      {isOpen && (
        <span className="info-popup-card" role="note">
          <button
            className="info-popup-close"
            type="button"
            aria-label="Close explanation popup"
            onClick={(event) => {
              event.stopPropagation();
              setIsOpen(false);
            }}
          >
            ×
          </button>
          <strong>{title}</strong>
          <span>{content}</span>
        </span>
      )}
    </span>
  );
}
