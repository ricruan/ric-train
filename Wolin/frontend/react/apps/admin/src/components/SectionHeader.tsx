import { useState } from 'react';

interface Props {
  id: string;
  label: string;
  defaultCollapsed?: boolean;
  collapsed?: boolean;
  onToggle?: (id: string) => void;
}

export default function SectionHeader({ id, label, defaultCollapsed = false, collapsed: controlledCollapsed, onToggle }: Props) {
  const [internalCollapsed, setInternalCollapsed] = useState(defaultCollapsed);
  const collapsed = controlledCollapsed !== undefined ? controlledCollapsed : internalCollapsed;
  const toggle = () => {
    if (onToggle) onToggle(id);
    else setInternalCollapsed((p) => !p);
  };
  return (
    <button className="section-header" onClick={toggle}>
      <span className="section-label">{label}</span>
      <svg className={`chevron ${collapsed ? '' : 'rotated'}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M6 9l6 6 6-6" />
      </svg>
    </button>
  );
}
