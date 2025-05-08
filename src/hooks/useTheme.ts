
import { useState, useEffect } from 'react';

type Theme = 'dark' | 'light' | 'system';

export function useTheme() {
  const [theme, setTheme] = useState<Theme>(
    () => (localStorage.getItem('theme') as Theme) || 'system'
  );
  
  const [resolvedTheme, setResolvedTheme] = useState<'dark' | 'light'>(
    () => getSystemTheme()
  );
  
  useEffect(() => {
    const root = window.document.documentElement;
    
    // Remove old theme class
    root.classList.remove('dark', 'light');
    
    // Apply new theme
    const newTheme = theme === 'system' ? getSystemTheme() : theme;
    root.classList.add(newTheme);
    setResolvedTheme(newTheme);
    
    // Save to localStorage
    localStorage.setItem('theme', theme);
  }, [theme]);
  
  // Listen for system theme changes
  useEffect(() => {
    if (theme !== 'system') return;
    
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    
    const handleChange = () => {
      setResolvedTheme(getSystemTheme());
      document.documentElement.classList.remove('dark', 'light');
      document.documentElement.classList.add(getSystemTheme());
    };
    
    mediaQuery.addEventListener('change', handleChange);
    return () => mediaQuery.removeEventListener('change', handleChange);
  }, [theme]);
  
  return { 
    theme, 
    setTheme, 
    resolvedTheme 
  };
}

function getSystemTheme(): 'dark' | 'light' {
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}
