
window.addEventListener('DOMContentLoaded', () => {
  const toggleButton = document.querySelector('#theme-toggle')
  const toggleIcon = toggleButton.querySelector('iconify-icon')
  
  let theme
  let toggleTimeout

  // methods
  const getDefaultTheme = () => window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
  
  const getStoredTheme = () => localStorage.getItem('theme')
  const setStoredTheme = () => localStorage.setItem('theme', theme)

  const themeUpdate = (transition) => {
    const icon = (transition ? {
      dark: 'line-md:sunny-outline-to-moon-transition',
      light: 'line-md:moon-to-sunny-outline-transition'
    } : {
      dark: 'line-md:moon',
      light: 'line-md:sunny-outline'
    })[theme]

    toggleIcon.setAttribute('icon', icon)

    document.documentElement.setAttribute('data-bs-theme', theme)

    if(!transition) return

    clearTimeout(toggleTimeout)
    document.documentElement.setAttribute('data-toggling', true)
    toggleTimeout = setTimeout(() => {
      document.documentElement.setAttribute('data-toggling', false)
    }, 1000)
  }

  const toggleTheme = () => {
    theme = theme === 'dark' ? 'light' : 'dark'
    setStoredTheme()
    themeUpdate(true)
  }

  // initialize theme
  theme = getStoredTheme()
  if(!theme) {
    theme = getDefaultTheme()
    setStoredTheme()
  }
  themeUpdate(false)

  // events
  toggleButton.addEventListener('click', toggleTheme)
})