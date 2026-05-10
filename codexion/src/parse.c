#include "codexion.h"
#include <stdlib.h>
#include <string.h>

static int	is_pos_int(const char *s)
{
	int	i;

	i = 0;
	if (!s[i])
		return (0);
	while (s[i])
	{
		if (s[i] < '0' || s[i] > '9')
			return (0);
		i++;
	}
	return (1);
}

int	parse_args(int ac, char **av, t_sim *sim)
{
	if (ac != 9)                     /* programme + 8 args */
		return (1);
	if (!is_pos_int(av[1]) || !is_pos_int(av[2]) || !is_pos_int(av[3])
		|| !is_pos_int(av[4]) || !is_pos_int(av[5]) || !is_pos_int(av[6])
		|| !is_pos_int(av[7]))
		return (1);
	sim->n = atoi(av[1]);
	sim->ttb = atoi(av[2]);
	sim->ttc = atoi(av[3]);
	sim->ttd = atoi(av[4]);
	sim->ttr = atoi(av[5]);
	sim->req_comp = atoi(av[6]);
	sim->dcd = atoi(av[7]);
	if (sim->n < 1 || sim->ttb < 1 || sim->ttc < 1
		|| sim->ttd < 1 || sim->ttr < 1 || sim->req_comp < 0
		|| sim->dcd < 0)
		return (1);
	if (strcmp(av[8], "fifo") == 0)
		sim->sched = FIFO;
	else if (strcmp(av[8], "edf") == 0)
		sim->sched = EDF;
	else
		return (1);
	return (0);
}