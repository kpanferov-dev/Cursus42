#include "codexion.h"
#include <stdlib.h>

static int	cmp(t_req a, t_req b, t_sched sched)
{
	if (a.priority != b.priority)
		return (a.priority < b.priority);
	return (a.coder_id < b.coder_id);
	(void)sched;
}

void	pq_init(t_pqueue *pq, int cap)
{
	pq->data = malloc(sizeof(t_req) * (cap + 1));
	pq->capacity = cap;
	pq->size = 0;
}

void	pq_destroy(t_pqueue *pq)
{
	free(pq->data);
}

void	pq_push(t_pqueue *pq, int coder_id, int prio, t_sched sched)
{
	int	i, parent;
	t_req	tmp;

	i = ++pq->size;
	tmp.coder_id = coder_id;
	tmp.priority = prio;
	while (i > 1)
	{
		parent = i / 2;
		if (cmp(tmp, pq->data[parent], sched))
		{
			pq->data[i] = pq->data[parent];
			i = parent;
		}
		else
			break ;
	}
	pq->data[i] = tmp;
}

t_req	pq_pop(t_pqueue *pq)
{
	t_req	top, last;
	int		i, child;

	top = pq->data[1];
	last = pq->data[pq->size--];
	i = 1;
	while (i * 2 <= pq->size)
	{
		child = i * 2;
		if (child + 1 <= pq->size
			&& pq->data[child + 1].priority < pq->data[child].priority)
			child++;
		if (last.priority <= pq->data[child].priority)
			break ;
		pq->data[i] = pq->data[child];
		i = child;
	}
	pq->data[i] = last;
	return (top);
}

int	pq_is_empty(t_pqueue *pq)
{
	return (pq->size == 0);
}

void	pq_remove_coder(t_pqueue *pq, int coder_id)
{
	int	i;

	i = 1;
	while (i <= pq->size)
	{
		if (pq->data[i].coder_id == coder_id)
		{
			if (i != pq->size)
				pq->data[i] = pq->data[pq->size];
			pq->size--;
			return ;
		}
		i++;
	}
}