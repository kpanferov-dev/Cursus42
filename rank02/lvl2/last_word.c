/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   last_word.c                                        :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: Kirill <kpanfero@student.42madrid.com>     +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2025/12/10 18:04:31 by Kirill            #+#    #+#             */
/*   Updated: 2025/12/10 18:04:31 by Kirill           ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

void last_word(char *str)
{
    int i = 0;
    int end;
    int start;
    
    while (str[i])
        i++;
    i--;


    while (i >= 0 && str[i] == ' ')
        i--;
    end = i;

   
    while (i >= 0 && str[i] != ' ')
        i--;
    start = i + 1;

    while (start <= end)
    {
        write(1, &str[start], 1);
        start++;
    }

}

int main(int c,int **v)
{
    if(c == 2)
        last_word(v[1]);
    write(1,"\n",1);
    return 0;
}