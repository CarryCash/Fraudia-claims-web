import { NavLink } from 'react-router-dom';

interface TopBarProps {
  isSidebarOpen: boolean;
}

export default function TopBar({ isSidebarOpen }: TopBarProps) {
  return (
    <header 
      className={`fixed top-0 right-0 h-16 bg-surface border-b border-outline-variant flex justify-between items-center px-gutter z-20 transition-all duration-300 ${isSidebarOpen ? 'left-[240px]' : 'left-[80px]'}`}
    >
      <div className="flex items-center gap-8">
        <div className="relative">
          <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant text-[20px]" data-icon="search">search</span>
          <input className="bg-surface-container-low border border-outline-variant rounded-lg pl-10 pr-4 py-1.5 w-80 text-body-md focus:border-primary focus:ring-0 transition-all" placeholder="Buscar siniestro, entidad o póliza..." type="text" />
        </div>
        <nav className="hidden md:flex gap-6">
          <NavLink to="/" className={({ isActive }) => `font-label-md py-5 transition-opacity ${isActive ? 'text-primary border-b-2 border-primary' : 'text-on-surface-variant hover:text-primary'}`}>
            Dashboard & Claims
          </NavLink>
          <NavLink to="/entities" className={({ isActive }) => `font-label-md py-5 transition-opacity ${isActive ? 'text-primary border-b-2 border-primary' : 'text-on-surface-variant hover:text-primary'}`}>
            Entities
          </NavLink>
          <NavLink to="/reports" className={({ isActive }) => `font-label-md py-5 transition-opacity ${isActive ? 'text-primary border-b-2 border-primary' : 'text-on-surface-variant hover:text-primary'}`}>
            Reports
          </NavLink>
        </nav>
      </div>
      <div className="flex items-center gap-4">
        <button className="p-2 text-on-surface-variant hover:text-primary transition-colors">
          <span className="material-symbols-outlined" data-icon="notifications">notifications</span>
        </button>
        <button className="p-2 text-on-surface-variant hover:text-primary transition-colors">
          <span className="material-symbols-outlined" data-icon="more_vert">more_vert</span>
        </button>
        <div className="h-8 w-8 rounded-full overflow-hidden bg-surface-container-highest border border-outline-variant">
          <img alt="Investigator Avatar" className="w-full h-full object-cover" src="https://lh3.googleusercontent.com/aida-public/AB6AXuAgJbOMgvqFxEXUWaxqfd3vMgVqVI__VidWmC8rq2pK2xo6LWe73KTarQxicezk0EHi-uGLX7CKubnqMw-SKz3Odu9y4smWhoKXrvt7MY8hwFsZykwNu63gHmFjF5pDL09GWQsBDlkRWfm8q3m7LsOUL5yVUruaPQQYYh0Fz7_GVYmRMNuvCKMHHWNp3qARplp_cywdC1mUbYPFlWorR-dJPyCOGSU3cLX1dawAFfZjq4PI2qLAHLJNokq2L7XUmTp-8OW28QQXcNg" />
        </div>
      </div>
    </header>
  );
}
