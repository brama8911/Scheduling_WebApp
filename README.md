# Work schedule manager

## Description:
The work schedule manager is a Flask-app that facilitates resp. automates the creation of the monthly work schedule and distribution of tasks for my company, which works with a group of freelancers. As soon as a freelancer has been initialized in the database, they can register and later log in to the programme. 

### index
On the index site every freelancer can see all of their individual tasks for the current month.

### abwesenheiten
In this section every freelancer can let the company know when they can not or do not want to work resp. when they are willing to be assigned tasks. Whichever field they put an "x" into indicates a day where they do not work. The users can only update their own fields. Every input will be stored in the database and will be visible for all the users.

### dienstplan
This is the heart of the programme. As long as there are no tasks, admin users can import a .csv file with the collected tasks for a month. This tasks then are saved in a database table, which will be created by the programme for every month. Then, admin users can create the schedule for the whole month. The code consideres the days the freelancers do not want to work as well as their desired workload resp. the number of days they want to work per week/month. Therefore, amongst the people available on a certain day the programme will choose one randomly, taking into account weighted probabilities. However, as per this weighted random choice the distribution of tasks is not necessarily fair, the programme creates many schedules and chooses the best one. 

### stats
This is a control site with some statistics of the current work schedule. It provides information on how well the automatically generated schedule meets the wishes of the freelancers regarding their desired amount of work days, and also on how fair task are distributed, taking into account the time required for a task or a day of more than one task and the money earned per work day. Based on this information the programme chooses the best resp. fairest of the generated schedules and also shows where manual changes might be needed in order to ensure company peace.

### team
On this site information about the freelancer team is given. Each of the freelancers can update only their own data, i.e. the amount of days they want to work per week. Admin users can update data for all freelancers as well as add new freelancers or delete the ones that dropped out of the company. Every change made here will update the respective database table.

