import { useEffect, useRef } from 'react';

interface UseModalFocusOptions {
  isOpen: boolean;
  onClose: () => void;
  initialFocusRef?: React.RefObject<HTMLElement | null>;
}

/**
 * Custom hook to ensure robust modal focus management:
 * 1. Focus Containment (Tab and Shift+Tab wrap within modal)
 * 2. Escape key dismissal
 * 3. Initial focus placement
 * 4. Automatic focus restoration to the triggering control upon dismissal
 */
export function useModalFocus({ isOpen, onClose, initialFocusRef }: UseModalFocusOptions) {
  const containerRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!isOpen) return;

    // 1. Remember triggering element to restore focus when modal closes
    triggerRef.current = document.activeElement as HTMLElement;

    // 2. Set initial focus after DOM render
    const timer = setTimeout(() => {
      if (initialFocusRef?.current) {
        initialFocusRef.current.focus();
      } else if (containerRef.current) {
        const focusables = getFocusableElements(containerRef.current);
        if (focusables.length > 0) {
          focusables[0].focus();
        }
      }
    }, 40);

    // 3. Handle keyboard navigation (Escape + Focus Trap)
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        e.stopPropagation();
        onClose();
        return;
      }

      if (e.key === 'Tab' && containerRef.current) {
        const focusables = getFocusableElements(containerRef.current);
        if (focusables.length === 0) {
          e.preventDefault();
          return;
        }

        const first = focusables[0];
        const last = focusables[focusables.length - 1];

        if (e.shiftKey) {
          if (document.activeElement === first || !containerRef.current.contains(document.activeElement)) {
            e.preventDefault();
            last.focus();
          }
        } else {
          if (document.activeElement === last || !containerRef.current.contains(document.activeElement)) {
            e.preventDefault();
            first.focus();
          }
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);

    return () => {
      clearTimeout(timer);
      window.removeEventListener('keydown', handleKeyDown);

      // 4. Restore focus back to the triggering control
      if (triggerRef.current && typeof triggerRef.current.focus === 'function') {
        triggerRef.current.focus();
      }
    };
  }, [isOpen, onClose, initialFocusRef]);

  return containerRef;
}

function getFocusableElements(container: HTMLElement): HTMLElement[] {
  const selector = 'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';
  return Array.from(container.querySelectorAll<HTMLElement>(selector)).filter(
    (el) => el.offsetParent !== null && !el.hasAttribute('aria-hidden')
  );
}
