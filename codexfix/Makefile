NAME		= codexion

CC			= cc
CFLAGS		= -Wall -Wextra -Werror
LDFLAGS		= -pthread

SRCS		= codexion_main.c \
			  codexion_init.c \
			  codexion_utils.c \
			  codexion_heap.c \
			  codexion_heap2.c \
			  codexion_dongle.c \
			  codexion_coder.c \
			  codexion_monitor.c

OBJS		= $(SRCS:.c=.o)

all:		$(NAME)

$(NAME):	$(OBJS)
			$(CC) $(CFLAGS) $(OBJS) -o $(NAME) $(LDFLAGS)

%.o:		%.c codexion.h
			$(CC) $(CFLAGS) -c $< -o $@

clean:
			rm -f $(OBJS)

fclean:		clean
			rm -f $(NAME)

re:			fclean all

.PHONY:		all clean fclean re
