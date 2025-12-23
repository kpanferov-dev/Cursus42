# **************************************************************************** #
#                                                                              #
#                                                         :::      ::::::::    #
#    Makefile                                           :+:      :+:    :+:    #
#                                                     +:+ +:+         +:+      #
#    By: kpanfero <kpanfero@student.42.fr>          +#+  +:+       +#+         #
#                                                 +#+#+#+#+#+   +#+            #
#    Created: 2025/12/07 12:32:26 by Kirill            #+#    #+#              #
#    Updated: 2025/12/08 09:24:03 by kpanfero         ###   ########.fr        #
#                                                                              #
# **************************************************************************** #

NAME = push_swap

SRC = src/push.c \
	  src/reverse.c \
	  src/rotate.c \
	  src/swap.c \
	  push_swap_utils.c \
	  parser.c \
	  sort_small.c \
	  sort_big.c \
	  sort_utils.c \
	  push_swap.c \

LIBFT_DIR = ./libft
LIBFT = $(LIBFT_DIR)/libft.a

INCLUDE = ./push_swap.h

OBJ = $(SRC:.c=.o)

CC = cc
CFLAGS = -Wall -Wextra -Werror
INCLUDES = -I./include -I$(LIBFT_DIR)

all: $(NAME)

$(NAME): $(OBJ) $(LIBFT)
	$(CC) $(CFLAGS) $(OBJ) $(LIBFT) -o $(NAME)

$(LIBFT):
	make -C $(LIBFT_DIR)

%.o: %.c
	$(CC) $(CFLAGS) $(INCLUDES) -c $< -o $@

clean:
	rm -f $(OBJ)
	make -C $(LIBFT_DIR) clean

fclean: clean
	rm -f $(NAME)
	make -C $(LIBFT_DIR) fclean

re: fclean all

.PHONY: all clean fclean re