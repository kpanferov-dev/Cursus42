#include "codexion.h"
#include <stdlib.h>
#include <string.h>
#include <stdio.h>

static void	launch_threads(t_sim *sim)
{
	int	i;

	i = 0;
	while (i < sim->n)
	{
		pthread_create(&sim->coders[i].thread, NULL, coder_routine,
			(void *)&sim->coders[i]);
		i++;
	}
	pthread_create(&sim->monitor, NULL, monitor_routine, (void *)sim);
}

static void	join_threads(t_sim *sim)
{
	int	i;

	i = 0;
	while (i < sim->n)
	{
		pthread_join(sim->coders[i].thread, NULL);
		i++;
	}
	pthread_join(sim->monitor, NULL);
}

int	main(int ac, char **av)
{
	t_sim	sim;

	memset(&sim, 0, sizeof(t_sim));
	if (parse_args(ac, av, &sim))
	{
		fprintf(stderr, "Error: invalid arguments\n");
		return (1);
	}
	sim_init(&sim);
	launch_threads(&sim);
	join_threads(&sim);
	sim_destroy(&sim);
	return (0);
}