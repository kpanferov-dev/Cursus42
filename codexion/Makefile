NAME = codexion
CC = cc
CFLAGS = -Wall -Wextra -Werror -pthread -fsanitize=thread
# -g3(te dice la linea) -O0(te dice la traza) -fsanitize=leak -fsanitize=thread o uno u otro pero no los dos y no mezclar con valgrind
SRCS = codexion.c
OBJS = $(SRCS:.c=.o)

all: $(NAME)

$(NAME): $(OBJS)
	$(CC) $(CFLAGS) -o $(NAME) $(OBJS)

clean:
	rm -f $(OBJS)

fclean: clean
	rm -f $(NAME)

re: fclean all

.PHONY: all clean fclean re