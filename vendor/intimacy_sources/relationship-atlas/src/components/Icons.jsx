const Icon = ({ children, size = 20, ...props }) => (
  <svg aria-hidden="true" viewBox="0 0 24 24" width={size} height={size} fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" {...props}>
    {children}
  </svg>
)

export const SearchIcon = (props) => <Icon {...props}><circle cx="11" cy="11" r="7" /><path d="m20 20-4-4" /></Icon>
export const FilterIcon = (props) => <Icon {...props}><path d="M4 6h16M7 12h10M10 18h4" /><circle cx="8" cy="6" r="1.4" fill="currentColor" stroke="none" /><circle cx="15" cy="12" r="1.4" fill="currentColor" stroke="none" /><circle cx="12" cy="18" r="1.4" fill="currentColor" stroke="none" /></Icon>
export const ExternalIcon = (props) => <Icon {...props}><path d="M14 5h5v5M12 12l7-7" /><path d="M19 13v5a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1h5" /></Icon>
export const LinkIcon = (props) => <Icon {...props}><path d="M10 13a5 5 0 0 0 7.5.5l2-2a5 5 0 0 0-7-7l-1.1 1.1" /><path d="M14 11a5 5 0 0 0-7.5-.5l-2 2a5 5 0 0 0 7 7l1.1-1.1" /></Icon>
export const DownloadIcon = (props) => <Icon {...props}><path d="M12 3v12m-4-4 4 4 4-4" /><path d="M5 19h14" /></Icon>
export const InfoIcon = (props) => <Icon {...props}><circle cx="12" cy="12" r="9" /><path d="M12 11v6" /><path d="M12 7h.01" /></Icon>
export const CloseIcon = (props) => <Icon {...props}><path d="m6 6 12 12M18 6 6 18" /></Icon>
export const ChevronIcon = ({ direction = 'right', ...props }) => {
  const transform = { right: 'rotate(0 12 12)', down: 'rotate(90 12 12)', left: 'rotate(180 12 12)', up: 'rotate(270 12 12)' }[direction]
  return <Icon {...props}><path d="m9 5 7 7-7 7" transform={transform} /></Icon>
}
export const PlusIcon = (props) => <Icon {...props}><path d="M12 5v14M5 12h14" /></Icon>
export const TrashIcon = (props) => <Icon {...props}><path d="M4 7h16M9 7V4h6v3M7 7l1 13h8l1-13" /></Icon>
export const ShieldIcon = (props) => <Icon {...props}><path d="M12 3 5 6v5c0 5 3 8 7 10 4-2 7-5 7-10V6l-7-3Z" /><path d="m9 12 2 2 4-4" /></Icon>
export const OfflineIcon = (props) => <Icon {...props}><path d="M7 18h10a4 4 0 0 0 .7-7.94A6 6 0 0 0 6.1 8.5 4.5 4.5 0 0 0 7 18Z" /><path d="M12 10v6m-2-2 2 2 2-2" /></Icon>
