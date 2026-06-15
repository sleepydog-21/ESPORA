window.dash_clientside = window.dash_clientside || {};

window.dash_clientside.calendar = {
    initCalendar: function(events, div_id) {
        console.log("DEBUG JS: initCalendar called with events:", events);
        if (!events || !div_id) return window.dash_clientside.no_update;
        
        var calendarEl = document.getElementById(div_id);
        if (!calendarEl) {
            console.log("DEBUG JS: calendarEl not found!");
            return window.dash_clientside.no_update;
        }

        // If calendar already exists, just update events
        if (calendarEl.calendar) {
            calendarEl.calendar.getEventSources().forEach(function(src) {
                src.remove();
            });
            calendarEl.calendar.addEventSource(events);
            return window.dash_clientside.no_update;
        }
        
        function updateDashInput(id, value) {
            if (window.dash_clientside && window.dash_clientside.set_props) {
                window.dash_clientside.set_props(id, {value: value});
            } else {
                var input = document.getElementById(id);
                if (input) {
                    var nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
                    nativeInputValueSetter.call(input, value);
                    input.dispatchEvent(new Event('input', { bubbles: true }));
                }
            }
        }

        // Initialize new calendar
        var calendar = new FullCalendar.Calendar(calendarEl, {
            locale: 'es',
            timeZone: 'UTC',
            initialView: 'timeGridWeek',
            slotMinTime: '06:00:00',
            headerToolbar: {
                left: 'prev,next today',
                center: 'title',
                right: 'dayGridMonth,timeGridWeek,timeGridDay'
            },
            buttonText: {
                today:    'Hoy',
                month:    'Mes',
                week:     'Semana',
                day:      'Día',
                list:     'Agenda'
            },
            editable: true, // allows dragging
            droppable: true,
            selectable: true,
            events: events,
            
            datesSet: function(info) {
                var rangeData = {
                    start: info.startStr,
                    end: info.endStr
                };
                updateDashInput('cal-view-range', JSON.stringify(rangeData));
            },
            
            eventDidMount: function(info) {
                info.el.addEventListener('contextmenu', function(e) {
                    e.preventDefault(); // Prevent default browser right-click menu
                    
                    // Create context menu div if it doesn't exist
                    var menu = document.getElementById('cal-context-menu');
                    if (!menu) {
                        menu = document.createElement('div');
                        menu.id = 'cal-context-menu';
                        menu.style.position = 'absolute';
                        menu.style.backgroundColor = 'white';
                        menu.style.border = '1px solid #ccc';
                        menu.style.boxShadow = '2px 2px 5px rgba(0,0,0,0.2)';
                        menu.style.zIndex = '9999';
                        menu.style.borderRadius = '4px';
                        menu.style.padding = '5px 0';
                        document.body.appendChild(menu);
                        
                        // Close menu when clicking elsewhere
                        document.addEventListener('click', function() {
                            menu.style.display = 'none';
                        });
                    }
                    
                    // Populate menu options
                    var eventId = info.event.id;
                    menu.innerHTML = `
                        <div class="cal-menu-item" data-status="scheduled" style="padding: 5px 15px; cursor: pointer;">⏳ Programada</div>
                        <div class="cal-menu-item" data-status="completed" style="padding: 5px 15px; cursor: pointer;">✅ Llevada a cabo</div>
                        <div class="cal-menu-item" data-status="cancelled" style="padding: 5px 15px; cursor: pointer;">❌ Cancelada</div>
                    `;
                    
                    // Add hover effects and click listeners
                    var items = menu.querySelectorAll('.cal-menu-item');
                    items.forEach(function(item) {
                        item.addEventListener('mouseenter', function() { this.style.backgroundColor = '#f0f0f0'; });
                        item.addEventListener('mouseleave', function() { this.style.backgroundColor = 'white'; });
                        item.addEventListener('click', function() {
                            var status = this.getAttribute('data-status');
                            var changeData = { id: eventId, status: status };
                            updateDashInput('cal-status-quick-change', JSON.stringify(changeData) + '_|ts|_' + new Date().getTime());
                            menu.style.display = 'none';
                        });
                    });
                    
                    // Position and show menu
                    menu.style.left = e.pageX + 'px';
                    menu.style.top = e.pageY + 'px';
                    menu.style.display = 'block';
                });
            },
            
            // Callbacks to Python via hidden inputs
            dateClick: function(info) {
                updateDashInput('cal-date-clicked', info.dateStr + '_' + new Date().getTime());
            },
            
            eventClick: function(info) {
                updateDashInput('cal-event-clicked', info.event.id + '_' + new Date().getTime());
            },
            
            eventDrop: function(info) {
                var dropData = {
                    id: info.event.id,
                    start: info.event.startStr,
                    end: info.event.endStr || info.event.startStr
                };
                updateDashInput('cal-event-dropped', JSON.stringify(dropData) + '_|ts|_' + new Date().getTime());
            }
        });
        
        calendar.render();
        calendarEl.calendar = calendar; // store reference

        return window.dash_clientside.no_update;
    }
}
