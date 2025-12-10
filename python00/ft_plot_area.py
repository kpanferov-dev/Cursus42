# **************************************************************************** #
#                                                                              #
#                                                         :::      ::::::::    #
#    ft_plot_are.py                                     :+:      :+:    :+:    #
#                                                     +:+ +:+         +:+      #
#    By: Kirill <kpanfero@student.42madrid.com>     +#+  +:+       +#+         #
#                                                 +#+#+#+#+#+   +#+            #
#    Created: 2025/12/10 11:04:06 by Kirill            #+#    #+#              #
#    Updated: 2025/12/10 11:04:06 by Kirill           ###   ########.fr        #
#                                                                              #
# **************************************************************************** #

def ft_plot_area():
    length = int(input("Enter length: "))
    width = int(input("Enter width: "))
    area = length * width
    print(f"Plot area: {area}")