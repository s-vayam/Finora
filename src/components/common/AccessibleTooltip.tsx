import React, { useState, useId } from 'react';

interface AccessibleTooltipProps {
  content: string;
  children: React.ReactNode;
  className?: string;
}

/**
 * AccessibleTooltip provides keyboard-accessible, screen-reader friendly tooltips.
 * - Opens on mouse hover (mouseenter / mouseleave)
 * - Opens on keyboard focus (focus / blur)
 * - Dismisses on Escape key
 * - Uses role="tooltip" with aria-describedby for accessibility
 */
export const AccessibleTooltip: React.FC<AccessibleTooltipProps> = ({
  content,
  children,
  className = '',
}) => {
  const [isVisible, setIsVisible] = useState(false);
  const tooltipId = useId();

  return (
    <span
      className={`relative inline-flex items-center outline-none ${className}`}
      onMouseEnter={() => setIsVisible(true)}
      onMouseLeave={() => setIsVisible(false)}
      onFocus={() => setIsVisible(true)}
      onBlur={() => setIsVisible(false)}
      tabIndex={0}
      role="button"
      aria-describedby={isVisible ? tooltipId : undefined}
      onKeyDown={(e) => {
        if (e.key === 'Escape') {
          e.stopPropagation();
          setIsVisible(false);
        }
      }}
    >
      {children}
      {isVisible && (
        <span
          id={tooltipId}
          role="tooltip"
          className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2.5 py-1.5 text-[11px] font-medium leading-relaxed text-white bg-[#111111] rounded-lg shadow-xl border border-[#333333] z-50 pointer-events-none min-w-[190px] max-w-[280px] text-center animate-in fade-in zoom-in-95 duration-100"
        >
          {content}
          <span className="absolute top-full left-1/2 -translate-x-1/2 -mt-1 border-4 border-transparent border-t-[#111111]" />
        </span>
      )}
    </span>
  );
};
