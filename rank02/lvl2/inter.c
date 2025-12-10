/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   inter.c                                            :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: Kirill <kpanfero@student.42madrid.com>     +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2025/12/10 17:50:57 by Kirill            #+#    #+#             */
/*   Updated: 2025/12/10 17:50:57 by Kirill           ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

int	iter(char *str, char c, int len)
{
	int	i = 0;

	while (str[i] && (i < len || len == -1))
		if (str[i++] == c)
			return (1);
	return (0);
}

int main(int c, char **v)
{
    int	i;
    if(c == 3)
    {
        i = 0;
		while (v[1][i])
		{
			if (!iter(v[1], v[1][i], i) && iter(v[2], v[1][i], -1))
				write(1, &v[1][i], 1);
			i += 1;
		}
    }
    write(1,"\n",1);
    return 0;
}