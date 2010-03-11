#ifndef C_TEST
#include <Python.h>
#endif

#include <stdlib.h>
#include <stdio.h>
#include <string.h>

#ifndef initfunc_name
#define initcfunc_name initcparser
#endif
#ifndef cparser_name
#define cparser_name "cparser"
#endif

//#define WITH_FORMAT

/*
 * default root object if none of objects are present in object list
 */
#ifndef DEFAULT_ROOT
#define DEFAULT_ROOT "ROOT"
#endif

// eol characters
#define EOL "\r\n"
// whitespace characters
#define WS " \t"

/*
 * element type
 * ELEM_REAL -- real element (object or object argument)
 * ELEM_IMAG -- imaginary element (blanks, comments, etc)
 */
typedef enum elem_type_e {
	ELEM_REAL,
	ELEM_IMAG
} elem_type_t;

typedef struct arg_s {
	char *arg_start;
	int arg_len;
	char *val_start;
	int val_len;
	struct arg_s *next;
} arg_t;

#ifdef WITH_FORMAT
typedef enum fmt_type_e {
	FMT_STR, // just string
	FMT_VAL // object's attribute value
} fmt_type_t;

typedef struct fmt_s {
	fmt_type_t fmt_type;
	char *fmt_start;
	int fmt_len;
	int line_no;
	struct fmt_s *next;
} fmt_t;
#endif

typedef struct obj_s {
	elem_type_t elem_type;
	char *obj_type_start;
	int obj_type_len;
	arg_t *args;
	arg_t *last_arg;
#ifdef WITH_FORMAT
	fmt_t *fmt;
	fmt_t *last_fmt;
#endif
	struct obj_s *next;
} obj_t;

typedef struct obj_list_s {
	obj_t *first;
	obj_t *last;
} obj_list_t;

typedef enum parse_state_e {
	PARSE_OBJ = 1,
	PARSE_ARG = 2,
	PARSE_ERR = 4
} parse_state_t;

typedef struct parse_s {
	int state; // may be combination of parse_state_t
	obj_list_t *objects;
	char *s; // current position in parsing string
	char *err_msg;
	int line_no;
	char *beginning; // beginning of parsing string
#ifdef WITH_FORMAT
	fmt_t *cur_fmt; // current object format (head of list)
	fmt_t *last_fmt; // last element of object format list
#endif
} parse_t;

typedef parse_t *(*parse_function_t) (parse_t *);

#ifdef WITH_FORMAT
fmt_t *newfmt(fmt_type_t fmt_type, char *fmt_start, int fmt_len, int line_no)
{
	fmt_t *fmt = (fmt_t *) malloc(sizeof(*fmt));
	fmt->fmt_type = fmt_type;
	fmt->fmt_start = fmt_start;
	fmt->fmt_len = fmt_len;
	fmt->line_no = line_no;
	fmt->next = NULL;
	return fmt;
}

void freefmt(fmt_t *fmt)
{
	fmt_t *f;
	while (fmt) {
		f = fmt;
		fmt = fmt->next;
		free(f);
	}
}
#endif

obj_list_t *newobj_list(void)
{
	obj_list_t *ol = malloc(sizeof(*ol));
	ol->first = NULL;
	ol->last = NULL;
	return ol;
}

obj_t *newobj(char *obj_type, int obj_type_len, elem_type_t e_type)
{
	obj_t *o = (obj_t *) malloc(sizeof(*o));
	o->obj_type_start = obj_type;
	o->obj_type_len = obj_type_len;
	o->elem_type = e_type;
	o->args = NULL;
	o->last_arg = NULL;
	o->next = NULL;
	return o;
}

void addarg(obj_t *o, char *arg, int arg_l, char *val, int val_l)
{
	arg_t *a = (arg_t *) malloc(sizeof(*a));
	a->arg_start = arg;
	a->arg_len = arg_l;
	if (val && val_l) {
		a->val_start = val;
		a->val_len = val_l;
	} else {
		a->val_start = NULL;
		a->val_len = 0;
	}
	a->next = NULL;
	if (o->args == NULL)
		o->args = a;
	else
		o->last_arg->next = a;
	o->last_arg = a;
}

void addobj(obj_list_t *obj_list, obj_t *o)
{
	if (obj_list->first) {
		obj_list->last->next = o;
	} else {
		obj_list->first = o;
	}
	obj_list->last = o;
}

void freeobj(obj_t *o)
{
	arg_t *a = o->args;
	arg_t *b;
	while (a) {
		b = a;
		a = b->next;
		free(b);
	}
	o->args = NULL;
	o->last_arg = NULL;
#ifdef WITH_FORMAT
	freefmt(o->fmt);
	o->fmt = NULL;
	o->last_fmt = NULL;
#endif
	free(o);
}

void freeobj_list(obj_list_t *obj_list)
{
	obj_t *o = obj_list->first;
	obj_t *o0;
	while (o) {
		o0 = o;
		o = o->next;
		freeobj(o0);
	}
	obj_list->first = NULL;
	obj_list->last = NULL;
	free(obj_list);
}

parse_t *newparse(char *s, int state)
{
	parse_t *parse = (parse_t *) malloc(sizeof(*parse));
	parse->state = state;
	parse->s = parse->beginning = s;
	parse->objects = newobj_list();
	parse->err_msg = NULL;
	parse->line_no = 0;
#ifdef WITH_FORMAT
	parse->cur_fmt = NULL;
	parse->last_fmt = NULL;
#endif
	return parse;
}

void freeparse(parse_t *parse)
{
	freeobj_list(parse->objects);
	//free(parse->beginning);
	//if (parse->err_msg)
	//	free(parse->err_msg);
#ifdef WITH_FORMAT	
	freefmt(parse->cur_fmt);
	parse->cur_fmt = NULL;
	parse->last_fmt = NULL;
#endif
	free(parse);
}

char *alloccpy(char *src, int l)
{
	char *dst = (char *) malloc(l + 1);
	strncpy(dst, src, l);
	dst[l] = '\0';
	return dst;
}

void printobj(obj_t *o)
{
#ifdef WITH_FORMAT
	arg_t *a;
	fmt_t *fmt;
	char *fmt_s;
	for (fmt = o->fmt; fmt; fmt = fmt->next) {
		fmt_s = alloccpy(fmt->fmt_start, fmt->fmt_len);
		if (fmt->fmt_type == FMT_STR)
			printf("%s", fmt_s);
		else
			printf("${%s}", fmt_s);
		free(fmt_s);
	}
#endif
}

void printobj_list(obj_list_t *ol)
{
	obj_t *o;
	for (o = ol->first; o; o = o->next)
		printobj(o);
}

#ifdef WITH_FORMAT
parse_t *start_fmt(parse_t *parse)
{
	if (parse->cur_fmt)
		freefmt(parse->cur_fmt);
	parse->cur_fmt = NULL;
	parse->last_fmt = NULL;
	return parse;
}

parse_t *add_fmt(parse_t *parse, fmt_type_t fmt_type, char *fmt_start, int fmt_len)
{
	fmt_t *fmt = newfmt(fmt_type, fmt_start, fmt_len, parse->line_no);
	if (parse->cur_fmt == NULL)
		parse->cur_fmt = fmt;
	if (parse->last_fmt)
		parse->last_fmt->next = fmt;
	parse->last_fmt = fmt;
	return parse;
}

parse_t *save_fmt(parse_t *parse)
{
	obj_t *o;
	if (parse->objects->last)
		o = parse->objects->last;
	else
		return parse;
	o->fmt = parse->cur_fmt;
	o->last_fmt = parse->last_fmt;
	parse->cur_fmt = NULL;
	parse->last_fmt = NULL;
	return parse;
}
#endif

parse_t *parse_err(parse_t *parse, char *err_msg)
{
	parse->state = PARSE_ERR;
	parse->err_msg = err_msg;
	return parse;
}

parse_t *blanks(parse_t *parse)
{
#ifdef WITH_FORMAT
	int l = 0;
	char *s = parse->s;
#endif
	for (parse->s; *parse->s && isblank(*parse->s); parse->s++) {
#ifdef WITH_FORMAT
		l++;
#endif
		;
	}
#ifdef WITH_FORMAT
	// here we may add blanks to object or argument tree
	if (l > 0)
		parse = add_fmt(parse, FMT_STR, s, l);
#endif
	return parse;
}

parse_t *comment(parse_t *parse)
{
	if (*parse->s == '#' || *parse->s == ';') {
#ifdef WITH_FORMAT
		char *comm = parse->s;
		int l = 0;
#endif
		for (; *parse->s && !strchr(EOL, *parse->s); parse->s++) {
#ifdef WITH_FORMAT
			l++;
#endif
			;
		}
#ifdef WITH_FORMAT
		parse = add_fmt(parse, FMT_STR, comm, l);
#endif
	}
	return parse;
}

parse_t *post_comment(parse_t *parse)
{
	if (*parse->s == ';') {
#ifdef WITH_FORMAT
		int l = 0;
		char *comm = parse->s;
#endif
		for (; *parse->s && !strchr(EOL, *parse->s); parse->s++) {
#ifdef WITH_FORMAT
			l++;
#endif
			;
		}
#ifdef WITH_FORMAT
		parse = add_fmt(parse, FMT_STR, comm, l);
#endif
	}
	return parse;
}

parse_t *post_line(parse_t *parse)
{
	int l = 0;
#ifdef WITH_FORMAT
	char *s = parse->s;
#endif
	if (*parse->s == '\r') {
		*parse->s++;
		l++;
	}
	if (*parse->s == '\n') {
		*parse->s++;
		l++;
	}
	if (l > 0) {
#ifdef WITH_FORMAT
		parse = add_fmt(parse, FMT_STR, s, l);
#endif
		parse->line_no++;
	}
	return parse;
}

#ifdef WITH_FORMAT
parse_t *save_fmt_obj(parse_t *parse)
{
	if (parse->state & PARSE_OBJ && parse->cur_fmt) {
		addobj(parse->objects, newobj("__fmt__", strlen("__fmt__"), ELEM_IMAG));
		parse = save_fmt(parse);
	}
	return parse;
}
#endif

parse_t *parse_line(parse_function_t parse_f, parse_t *parse)
{
	parse = blanks(parse);
	//printf("b%d\n", parse->state);
#ifdef WITH_FORMAT
	parse = save_fmt_obj(parse);
#endif
	parse = comment(parse);
	//printf("c%d\n", parse->state);
#ifdef WITH_FORMAT
	parse = save_fmt_obj(parse);
#endif
	parse = parse_f(parse);
	//printf("f%d\n", parse->state);
	parse = post_comment(parse);
	//printf("p%d\n", parse->state);
#ifdef WITH_FORMAT
	parse = save_fmt_obj(parse);
#endif
	parse = post_line(parse);
#ifdef WITH_FORMAT
	parse = save_fmt_obj(parse);
#endif
	return parse;
}

/*
 * chech whether there are no garbage after
 */
parse_t *trailing_blanks(parse_t *parse)
{
	parse = blanks(parse);
	if (*parse->s && !strchr(EOL, *parse->s) && *parse->s != ';')
		parse = parse_err(parse, "Trailing characters");
	return parse;
}

parse_t *parse_object_obj(parse_t *parse)
{
	int obj_l = 0;
	char *obj_start;
	// empty
	if (!*parse->s || strchr(EOL WS, *parse->s))
		return parse;
#ifdef WITH_FORMAT
	parse = start_fmt(parse);
	char *def_start = parse->s;
#endif
	int def_len = strlen("define");
	if (strncmp(parse->s, "define", def_len) == 0)
		parse->s += def_len;
	else {
		parse = parse_err(parse, "Definition should start from 'define'");
		return parse;
	}
	if (!*parse->s || !isblank(*parse->s)) {
		parse = parse_err(parse, "Definition should start from 'define'");
		return parse;
	}
#ifdef WITH_FORMAT
	parse = add_fmt(parse, FMT_STR, def_start, def_len);
#endif
	parse = blanks(parse);
	obj_start = parse->s;
	for (; *parse->s && !strchr(EOL WS "{", *parse->s); parse->s++, obj_l++);
	if (obj_l == 0) {
		parse = parse_err(parse, "'define' should be followed by object name");
		return parse;
	}
#ifdef WITH_FORMAT
	parse = add_fmt(parse, FMT_STR, obj_start, obj_l);
#endif
	parse = blanks(parse);
	if (!*parse->s || *parse->s && *parse->s != '{') {
		parse = parse_err(parse, "Definition should end with '{'");
		return parse;
	}
#ifdef WITH_FORMAT
	parse = add_fmt(parse, FMT_STR, "{", 1);
#endif
	parse->s++;
	parse = trailing_blanks(parse);
	if (parse->state & PARSE_ERR)
		return parse;
	obj_t *o = newobj(obj_start, obj_l, ELEM_REAL);
	addobj(parse->objects, o);
	parse->state = PARSE_ARG;
	return parse;
}

parse_t *parse_object_arg(parse_t *parse)
{
	if (*parse->s == '}') {
#ifdef WITH_FORMAT
		parse = add_fmt(parse, FMT_STR, "}", 1);
#endif
		parse->s++;
		parse = trailing_blanks(parse);
#ifdef WITH_FORMAT
		parse = save_fmt(parse);
#endif
		if (!(parse->state & PARSE_ERR))
			parse->state = PARSE_OBJ;
		return parse;
	}
	int arg_l = 0;
	char *arg_start = parse->s;
	for (; *parse->s && !strchr(EOL WS, *parse->s); parse->s++, arg_l++);
	if (arg_l == 0)
		return parse;
#ifdef WITH_FORMAT
	parse = add_fmt(parse, FMT_STR, arg_start, arg_l);
#endif
	int val_l = 0;
	char *val_start = NULL;
	if (*parse->s && !strchr(EOL, *parse->s)) {
		parse = blanks(parse);
		val_start = parse->s;
		for (; *parse->s && *parse->s != ';' && !strchr(EOL, *parse->s); parse->s++, val_l++);
	} 
#ifdef WITH_FORMAT
	parse = add_fmt(parse, FMT_VAL, arg_start, arg_l);
#endif
	if (parse->objects->last == NULL) {
		obj_t *o = newobj(DEFAULT_ROOT, strlen(DEFAULT_ROOT), ELEM_REAL);
		addobj(parse->objects, o);
	}
	addarg(parse->objects->last, arg_start, arg_l, val_start, val_l);
	parse->state = PARSE_ARG;
	return parse;
}


parse_t *parse_status_obj(parse_t *parse)
{
	int l = 0;
	char *start = parse->s;
	for (; *parse->s && !strchr(EOL WS "{", *parse->s); parse->s++, l++);
	// empty line
	if (l == 0 && *parse->s && *parse->s != '{')
		return parse;
	if (strchr(EOL, *parse->s)) {
		parse = parse_err(parse, "Status object name should be followed by '{'");
		return parse;
	}
#ifdef WITH_FORMAT
	parse = start_fmt(parse);
	parse = add_fmt(parse, FMT_STR, start, l);
#endif
	parse = blanks(parse);
	if (*parse->s != '{') {
		parse = parse_err(parse, "Status object name should be followed by '{'");
		return parse;
	}
#ifdef WITH_FORMAT
	parse = add_fmt(parse, FMT_STR, "{", 1);
#endif
	parse->s++;
	parse->state = PARSE_ARG;
	// skip till trailing comment or \n, should be no garbage
	parse = trailing_blanks(parse);
	if (parse->state & PARSE_ERR)
		return parse;
	obj_t *o = newobj(start, l, ELEM_REAL);
	addobj(parse->objects, o);
	return parse;
}

parse_t *parse_status_arg(parse_t *parse)
{
	if (*parse->s == '}') {
#ifdef WITH_FORMAT
		parse = add_fmt(parse, FMT_STR, "}", 1);
#endif
		parse->s++;
		parse = trailing_blanks(parse);
#ifdef WITH_FORMAT
		parse = save_fmt(parse);
#endif
		if (!(parse->state & PARSE_ERR))
			parse->state = PARSE_OBJ;
		return parse;
	}
	int arg_l = 0;
	char *arg_start = parse->s;
	for (; *parse->s && !strchr(EOL WS "=", *parse->s); parse->s++, arg_l++);
	if (arg_l == 0 && *parse->s != '=')
		return parse;
#ifdef WITH_FORMAT
	parse = add_fmt(parse, FMT_STR, arg_start, arg_l);
#endif
	int val_l = 0;
	char *val_start = NULL;
	if (*parse->s && !strchr(EOL, *parse->s)) {
		parse = blanks(parse);
		if (*parse->s != '=') {
			parse = parse_err(parse, "Argument name should be followed by '='");
			return parse;
		}
#ifdef WITH_FORMAT
		parse = add_fmt(parse, FMT_STR, "=", 1);
#endif
		parse->s++;
		parse = blanks(parse);
		val_start = parse->s;
		for (; *parse->s && *parse->s != ';' && !strchr(EOL, *parse->s); parse->s++, val_l++);
	}
	if (parse->objects->last == NULL) {
		obj_t *o = newobj(DEFAULT_ROOT, strlen(DEFAULT_ROOT), ELEM_REAL);
		addobj(parse->objects, o);
	}
#ifdef WITH_FORMAT
	parse = add_fmt(parse, FMT_VAL, arg_start, arg_l);
#endif
	addarg(parse->objects->last, arg_start, arg_l, val_start, val_l);
	parse->state = PARSE_ARG;
	return parse;
}

parse_t *parse_string(parse_function_t parse_obj, parse_function_t parse_arg, parse_t *parse)
{
	while (*parse->s && !(parse->state & PARSE_ERR)) {
		switch (parse->state) {
			case PARSE_OBJ:
				parse = parse_line(parse_obj, parse);
				break;
			case PARSE_ARG:
				parse = parse_line(parse_arg, parse);
				break;
			default:
				parse = parse_err(parse, "In unknown state");
				break;
		}
	}
#ifdef WITH_FORMAT
	if (parse->cur_fmt)
		parse = save_fmt(parse);
#endif
	return parse;
}

#ifndef C_TEST

static PyObject *py_parse_string(parse_function_t parse_obj, parse_function_t parse_arg, PyObject *self, PyObject *args)
{
	const char *s;
	int lsz;
	const char *state;
	if (!PyArg_ParseTuple(args, "s#s", &s, &lsz, &state))
		return NULL;
	PyObject *py_ol = PyList_New(0);
        if (!lsz)
		return py_ol;
	int pstate;
	if (strcmp("PARSE_OBJ", state) == 0)
		pstate = PARSE_OBJ;
	else if (strcmp("PARSE_ARG", state) == 0)
		pstate = PARSE_ARG;
	else
		return NULL;
	parse_t *parse = newparse(s, pstate);
	parse = parse_string(parse_obj, parse_arg, parse);
	if (parse->err_msg) {
		PyErr_Format(PyExc_Exception, "%s at line %d", parse->err_msg, parse->line_no);
		freeparse(parse);
		return NULL;
	}
	obj_t *o;
	arg_t *a;
#ifdef WITH_FORMAT
	fmt_t *f;
#endif
	for (o = parse->objects->first; o; o = o->next) {

		PyObject *py_args = PyList_New(0);
		for (a = o->args; a; a = a->next) {

			PyObject *py_arg = Py_BuildValue("(s#s#)",
					a->arg_start, a->arg_len,
					a->val_start, a->val_len);

			PyList_Append(py_args, py_arg);

			Py_DECREF(py_arg);
		}

		PyObject *py_f;
#ifdef WITH_FORMAT
		py_f = PyList_New(0);
		for (f = o->fmt; f; f = f->next) {
			PyObject *py_fmt = Py_BuildValue("(ss#i)",
					f->fmt_type == FMT_VAL ? "FMT_VAL" : "FMT_STR",
					f->fmt_start, f->fmt_len,
					f->line_no);

			PyList_Append(py_f, py_fmt);

			Py_DECREF(py_fmt);
		}
#else
		py_f = Py_None;
		Py_INCREF(Py_None);
#endif

		PyObject *py_o = Py_BuildValue("(ss#NN)",
				o->elem_type == ELEM_REAL ? "ELEM_REAL" : "ELEM_IMAG",
				o->obj_type_start, o->obj_type_len,
				py_args,
				py_f);

		PyList_Append(py_ol, py_o);

		Py_DECREF(py_o);

	}
	freeparse(parse);

	return py_ol;
}

static PyObject *parse_status_string(PyObject *self, PyObject *args)
{
	return py_parse_string(parse_status_obj, parse_status_arg, self, args);
}

static PyObject *parse_object_string(PyObject *self, PyObject *args)
{
	return py_parse_string(parse_object_obj, parse_object_arg, self, args);
}

PyMethodDef methods[] = {
	{"parse_status_string", parse_status_string, METH_VARARGS, "Parse string containing all status values"},
	{"parse_object_string", parse_object_string, METH_VARARGS, "Parse string containing nagios objects"},
	{NULL, NULL, 0, NULL}
};

PyMODINIT_FUNC initfunc_name()
{
	PyObject *m;
	m = Py_InitModule(cparser_name, methods);

}

#endif
