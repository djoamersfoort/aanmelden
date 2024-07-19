const entries = JSON.parse(document.getElementById('entries').textContent)
entries.forEach(entry => entry.date = new Date(entry.date))

const slots = JSON.parse(document.getElementById('slots').textContent)
slots.forEach(slot => slot.date = new Date(slot.date))

const calendarTitle = document.querySelector('#calendar-title')
const calendarBody = document.querySelector('#calendar-body')

const STORAGE_KEY = 'calendar-date'
const storedDate = sessionStorage.getItem(STORAGE_KEY)
let currentDate = storedDate ? new Date(storedDate) : new Date()

const compareDates = (date1, date2) => (
    date1.getDate() === date2.getDate() &&
    date1.getMonth() === date2.getMonth() &&
    date1.getFullYear() === date2.getFullYear()
)

const formatDate = (date) => {
    const year = date.getFullYear()
    const month = date.getMonth() + 1
    const day = date.getDate() 
    return `${year}-${month}-${day}`
}

const loadCalendar = () => {
    const today = new Date()
    
    const year = currentDate.getFullYear()
    const month = currentDate.getMonth()
    const date = new Date(year, month)

    const nextMonth = new Date(date)
    nextMonth.setMonth(date.getMonth() + 1)

    calendarBody.textContent = ''
    calendarTitle.textContent = date.toLocaleDateString('nl-NL', { month: 'long', year: 'numeric' })
    
    // offset to start of week
    // if sunday, subtract extra week (otherwise week starts on the 2nd)
    const days = date.getDay() || 7
    date.setDate(-days + 2)

    while (date < nextMonth) {
        const tr = document.createElement('tr')
        calendarBody.append(tr)

        for (let i = 0; i < 7; i++) {
            const dateNum = date.getDate()
            
            const dateEntry = entries.find(entry => compareDates(date, entry.date))
            const dateSlot = slots.find(slot => slot.date.getDay() === date.getDay())

            const td = document.createElement('td')
            td.className = 'text-center position-relative'
            td.textContent = dateNum

            // if registration is found
            if (dateEntry) {
                const icon = document.createElement('iconify-icon')
                icon.setAttribute('noobserver', true)
                icon.setAttribute('icon', 'line-md:confirm-circle')
                icon.ariaHidden = 'true'
                icon.className = 'position-absolute top-0 end-0 m-1'
                td.append(icon)

                td.classList.add('text-bg-info')
            } else if(dateSlot) {
                td.classList.add('bg-secondary-subtle')
            }
            
            // make clickable if can register
            if(dateSlot) {
                const dateFormatted = formatDate(date)
                td.role = 'button'
                td.ariaLabel = `registreren voor ${dateFormatted}`

                const route = dateEntry ? 'deregister' : 'register'
                const dateParam = encodeURIComponent(dateFormatted)
                const dayParam = encodeURIComponent(dateSlot.name)
                const podParam = encodeURIComponent(dateSlot.pod)

                const url = `/${route}/future/${dateParam}/${dayParam}/${podParam}`
                
                td.addEventListener('click', () => location.href = url)
            }
            
            // if date is today
            if (compareDates(date, today)) {
                td.classList.add('text-decoration-underline')
            }

            // gray out if it isn't the current month
            if (date.getMonth() === month) {
                td.classList.add('fw-bold')
            } else {
                td.classList.add('opacity-25')
            }

            tr.append(td)
            date.setDate(dateNum + 1)
        }
    }
}

const nextMonth = (offset) => {
    currentDate.setMonth(currentDate.getMonth() + offset)
    sessionStorage.setItem(STORAGE_KEY, currentDate.toISOString())
    loadCalendar()
}

const resetMonth = () => {
    currentDate = new Date()
    sessionStorage.removeItem(STORAGE_KEY)
    loadCalendar()
}

loadCalendar()