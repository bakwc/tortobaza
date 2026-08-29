export function InstagramIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.4"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <rect x="3" y="3" width="18" height="18" rx="5" ry="5" />
      <circle cx="12" cy="12" r="4" />
      <circle cx="17.5" cy="6.5" r="1" fill="currentColor" stroke="none" />
    </svg>
  );
}

export function TelegramIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.4"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M21 5 3 11.5l6 2 2 6L21 5z" />
      <path d="m9 13.5 9-7" />
    </svg>
  );
}

export function WhatsAppIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.4"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z" />
      <path d="M8.5 9.5c0 3.5 3 6.5 6.5 6.5l1-1.5-2-1-1 1c-1.5-.5-2.5-1.5-3-3l1-1-1-2-1.5 1z" />
    </svg>
  );
}

export function YandexMapsIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" aria-hidden="true">
      <path
        fill="#FC3F1D"
        d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7z"
      />
      <circle cx="12" cy="9" r="2.5" fill="#fff" />
    </svg>
  );
}

export function GoogleMapsIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" aria-hidden="true">
      <path fill="#34A853" d="M12 22s7-7.75 7-13c0-1.07-.24-2.08-.67-3L12 12v10z" />
      <path fill="#FBBC04" d="M12 12 5.33 6A7.96 7.96 0 0 0 5 9c0 5.25 7 13 7 13V12z" />
      <path fill="#4285F4" d="M19 9c0-3.87-3.13-7-7-7v10l7-6.33C18.76 6.92 19 7.93 19 9z" />
      <path fill="#EA4335" d="M12 2C8.13 2 5 5.13 5 9c0 .35.03.69.08 1.02L12 12V2z" />
      <circle cx="12" cy="9" r="2.25" fill="#fff" />
    </svg>
  );
}
