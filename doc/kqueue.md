原文:https://www.freebsd.org/cgi/man.cgi?query=kqueue&apropos=0&sektion=0&manpath=FreeBSD+12.2-RELEASE+and+Ports&arch=default&format=html



kqueue, kevent -- 内核事件通知机制



库

标准c库 



接口

```c
#include <sys/event.h>
```

```c
int kqueue(void);
```

```c
int kevent(
	int	kq, 
	const struct kevent	*changelist, 
	int nchanges,
	struct	kevent *eventlist, 
	int nevents,
	const struct timespec *timeout
);
```

```c
EV_SET(kev, ident,	filter,	flags, fflags, data, udata);
```



描述：

​	事件发生、条件变动时, kqueue()系统调用提供了一套通知的通知机制，基于一小块内核代码的结果，这小块代码叫做过滤器(filters)。一个事件由(id, filter)对唯一标识。



​	一旦注册一个事件(kevent)，事件过滤器(filter)会马上执行，目的是为了检测是否存在之前的条件。

当一个事件(event)被传递到过滤器评估, 过滤器也会执行。如果过滤器认为条件应该上报，kevent会被放在kqueue上，等待用户来取。



​	当用户尝试从kqueue取kevent时，filter也会执行。如果filter表明触发事件的条件不再存在，kevent会从kqueue上移除。



多个事件触发一个filter并不会导致多个kevents，相反，filter会把多个事件合并成一个单一的kevent。如果存在一个文件描述符fd，调用close(fd)，kqueue会移除所有引用了这个fd的kevent。



kqueue() 系统调用: 创建一个内核事件队列(event queue)，返回一个描述符。通过fork创建的子进程不会继承这个事件队列。而通过rfork再加RFFDG标志，就可以。



kevent() 系统调用: 注册事件到队列，返回未决事件。

​	changelist: 指针，指向kevent结构数组。数组所有的改变都会被应用。

​	eventlist: 也是指向event结构数组.

​	nevents: 决定了eventlist的大小，如果是0, kevent()会马上返回, 即使有timeout参数。

​	timeout: 如果是一个非NULL的指针, 指定等待时间间隔, timespec结构; 如果是NULL指针, kevent()永久等待。



EV_SET() 宏: 初始化kevent结构



kevent结构如下：

```c
 struct kevent {
	     uintptr_t	ident;	     /*	identifier for this event */
	     short     filter;	     /*	filter for event */
	     u_short   flags;	     /*	action flags for kqueue	*/
	     u_int     fflags;	     /*	filter flag value */
	     int64_t   data;	     /*	filter data value */
	     void      *udata;	     /*	opaque user data identifier */
	     uint64_t  ext[4];	     /*	extensions */
     };
```

ident:  标识事件值,  它的值应该由附加的filter决定，但通常用文件描述符直接指定。



filter:  标识处理事件的内核filter，预定义的系统filter如下：



flags: 事件发生时, 要执行的动作；



fflags: filter特定标志；



data: filter特定数据；



udata: 用户自定义数据；

ext: 扩展数据，在内核与进程间传递. ext[0] ext[1] 由filter定义, 如果filter不用它们, 值不会变. ext[2] ext[3]总是由内核传过来, 为应用进程提供额外的上下文；



flags包含如下的值：

EV_ADD:  添加事件到kqueue. 重复添加一个存在的事件只会修改这个事件的参数，不会有两个事件。EV_ADD标志会自动包含EV_ENABLE标志，除非显示用EV_DISABLE标志。

EV_ENABLE: 如果事件触发了，允许kevent()返回事件。

EV_DISABLE: 如果事件触发了，kevent()不会返回事件, filter本身是正常的。

EV_DISPATCH: 事件被传递后，马上禁止事件来源，即不返回事件了。

EV_DELETE: 从kqueue移除事件, 附加到文件描述符上的事件会被自动移除。

EV_RECEIPT:  当需要对kqueue做批量修改时，不用等待所有未决事件完成就可修改。当作为输入传递, 会使得EV_ERROR返回.  当一个filter被成功添加， data字段会置零. 需要注意的是, 如果设定了这个标志, 而在eventlist里没有空间存EV_ERROR事件了，那么之后的事件不会被处理。

EV_ONESHOT: filter被首次触发时, 返回事件，待用户从kqueue取走事件后，从kqueue移除。

EV_CLEAR: 用户取走事件后, 状态会重置。

EV_EOF: filter特定EOF条件。



系统预定义filter，参数通过fflags和data传递：

EVFILE_READ: 接受一个描述符参数, 当有数据可读时返回. 不同的描述符类型，有不同的行为。

​	Sockets  对于传入listen()方法的sockets，每当有连接过来时返回，data包含listen backlog值。

​					对于其他的socket描述符, 当有数据可读时返回, 视SO_RECVLOWAT(接受缓冲区低水位)的大小，但这个SO_RECVLOWAT值可以被覆盖，通过 NOTE_LOWAT fflags标志，再加上data里新设置的值。返回时，data包含可以读的字节数。

​					如果读socket的这方关闭了，那么filter设置flags EV_EOF，并且返回socket error 放在fflags. 如果socket缓冲区还有未读数据，EOF会返回。

​	Vnodes	文件指针不在文件末尾时返回, data包含从当前位置到文件末尾的偏移量，可能是负值。

​					 需要通过设置NOTE_FILE_POLL fflags才可以像poll那样，读事件无条件触发。

​	Fifos, Pipes 有数据可读时返回, data包含可读字节数。

​						当最后一个写端断开时, filter会设置EV_EOF flags，但如果有新的写端连接, EV_EOF flags会被清除, 这个时候filter会恢复等待数据可读再返回，不会因为有EV_EOF就直接返回。

​	BPF devices	当BPF缓冲满了、BPF超时到期、BPF设置了"马上模式"并且可数据可读时返回，data包含可读字节数。



EVFILE_WRITE	接受一个描述符作为标识，当可以向描述符写时返回。对于sockets, pipes和fifos, data将包含写缓冲区的剩余空间。当读端断开时，filter会设置 EV_EOF。这个filter不支持vnodes 和BPF devices。

​							对于sockets，低水位标志设置与EVFILE_READ一样。



EVFILE_EMPTY	接受一个描述符作为标识, 当写缓冲区没有剩余空间时返回。



EVFILE_AIO	这个filter的事件不是直接由kevent()注册，而是通过aio_sigevent。

EVFILE_VNODE	接受一个描述符作为标识, 在fflags添加事件监听, 当一个或更多请求事件出现时返回，监听的事件包括：

​		NOTE_ATTRIB	描述符引用的文件属性变化时.

​		NOTE_CLOSE	文件描述符被关闭. 被关闭的描述符没有写权限.

​		NOTE_CLOSE_WRITE	文件描述符被关闭. 被关闭的描述符有写权限. 需要注意的是，通过unmount和revoke强制关闭，NOTE_CLOSE_WRITE与NOTE_CLOSE都不会触发，可以用NOTE_REVOKE触发.

​		NOTE_DELETE	在文件描述符上调用unlink()系统调用时.

​		NOTE_EXTEND	对于常规文件, 文件被扩展时; 对于目录, 添加/删除一条条目，或者重命名目录时. 

在目录内重命名不会触发NOTE_EXTEND.

​		NOTE_LINK	文件改变, 在一个目录内创建一个子目录，或者删除一个子目录.

​		NOTE_OPEN	文件描述符被打开.

​		NOTE_READ	文件出现了一次读

​		NOTE_RENAME	文件被重命名了.

​		NOTE_REVOKE	通过revoke()方法、或者被unmounted时

​		NOTE_WRITE	文件出现了一次写入.

​		作为返回, fflags包含触发了这个filter的事件列表。

EVFILE_PROC	接受一个要监控的进程id作为标识, 在fflags里设置事件，当这个进程出现这些事件时返回。如果一个进程能看到另一个进程，就能附加事件在另一个进程上。监听事件有：

​		NOTE_EXIT	进程退出，退出状态存在data中。

​		NOTE_FORK	进程调用了fork()方法。

​		NOTE_EXEC	进程通过execve()执行了一个新进程。

​		NOTE_TRACK	接着进程调用fork()，父进程注册一个新的kevent来监控子进程，使用同样的fflags。子进程会发送一个事件，事件包含NOTE_CHILD fflags，data包含父进程pid。如果父进程注册kevent失败(通常由于资源限制失败)，会触发NOTE_TRACKERR fflags事件，子进程也不会触发NOTE_CHILD事件。

​		作为返回，fflags包含触发了这个filter的事件列表。



EVFILE_PROCDESC	接受一个要监控的进程描述符（pdfork()创建）作为标识，fflags包含监听的事件，当进程出现事件时返回。监听的事件有：

​		NOTE_EXIT	进程退出，退出状态存在data里。

​		作为返回，fflags包含触发了这个filter的事件列表。



EVFILE_SIGNAL	接受要监控的信号数字作为标识，当给定的信号被传递到进程时返回。与signal()、sigaction()共存，优先级更低。这个filter会记录所有尝试给进程发送的信号，即使这个信号被设置成SIG_IGN，有个例外，SIGCHLD信号, 对于SIGCHLD信号，如果设置了SIG_IGN，将不会被filter记录。在信号被传递给进程后，事件通知产生，data表示自上次调用kevent()时，信号产生的次数。这个filter将自动设置EV_CLEAR flag。



EVFILE_TIMER	任意定时器，添加一个定时器时，data指一个时刻、或者超时时段，来触发定时器。除非指定EV_ONESHOT或NOTE_ABSTIME，否则定时器将会是周期性的触发。作为返回，data包含自上次调用kevent()时的超时次数。对于非单调性的定时器，这个filter自动设置EV_CLEAR flag。这个filter接受以下标志，作为fflags参数：

​			NOTE_SECONDS	data是秒

​			NOTE_MSECONDS	data是毫秒

​			NOTE_USECONDS	data是微秒

​			NOTE_NESCONDS	data是纳秒

​			NOTE_ABSTIME	绝对过期时间

​			如果没有设置fflags，默认是毫秒。作为返回，fflags包含触发了这个filter的事件列表。

​			如果重复添加一个已存在的定时器，现存的定时器会被取消，并用新设置的fflags data参数重新启动定时器。

​			系统有最大定时器数量限制，由kern.kq_calloutmax控制。



EVFILE_USER	用户事件, 参数ident标识这个事件，并且ident不能与任何内核机制关联，由用户层面代码触发。fflags低24位被用来定义flags，并且通过如下方法操作flags：

​			NOTE_FFNOP	忽略输入fflags

​			NOTE_FFAND	按位与 fflags

​			NOTE_FFOR	按位 或 fflags

​			NOTE_FFCOPY	复制fflags

​			NOTE_FFCTRLMASK	控制fflags的掩码

​			NOTE_FFLAGSMASK	用户定义fflags掩码

​			用户事件被触发：

​			NOTE_TRIGGER	导致事件被触发。

​			作为返回，fflags低24位包含用户定义flags。



取消的行为

​	如果nevents非0，函数阻塞, 这次调用是一个可取消点。否则如果nevents是0，这次调用不可取消。可取消只能发现在在对kqueue作任何改变前发生，或者调用阻塞时，kqueue没有改变请求。



返回值

​	kqueue()系统调用创建一个新的内核事件队列，返回一个文件描述符。如果有错误，将返回-1，并设置error。

​	kevent()系统调用返回放在eventlist里的事件数量，eventlist大小由nevents决定。如果在处理changelist元素里发生错误，并且在eventlist有足够的空间，会在eventlist里放一个EV_ERROR flags事件，其中data包含系统错误，如果eventlist没有足够的空间了，返回-1，并设置errno。如果定时器到期了，kevent()返回0。



粟子

```c
#include <sys/event.h>
#include <err.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(int argc, char **argv) {
	 struct	kevent event;	 /* Event we want to monitor */
	 struct	kevent tevent;	 /* Event triggered */
	 int kq, fd, ret;

	 if (argc != 2)
	     err(EXIT_FAILURE, "Usage: %s path\n", argv[0]);
	 fd = open(argv[1], O_RDONLY);
	 if (fd	== -1)
	     err(EXIT_FAILURE, "Failed to open '%s'", argv[1]);

	 /* Create kqueue. */
	 kq = kqueue();
	 if (kq	== -1)
	     err(EXIT_FAILURE, "kqueue() failed");
  
  // EV_SET(kev, ident,	filter,	flags, fflags, data, udata);
	 /* Initialize kevent structure. */
	 EV_SET(&event,	fd, EVFILT_VNODE, EV_ADD | EV_CLEAR, NOTE_WRITE, 0,	NULL);
	 /* Attach event to the	kqueue.	*/
	 ret = kevent(kq, &event, 1, NULL, 0, NULL);
	 if (ret == -1)
	     err(EXIT_FAILURE, "kevent register");
	 if (event.flags & EV_ERROR)
	     errx(EXIT_FAILURE,	"Event error: %s", strerror(event.data));

	 for (;;) {
	     /*	Sleep until something happens. */
	     ret = kevent(kq, NULL, 0, &tevent,	1, NULL);
	     if	(ret ==	-1) {
		 			err(EXIT_FAILURE, "kevent wait");
	     } else if (ret > 0) {
		 			printf("Something was written in '%s'\n", argv[1]);
	     }
	 }
}
```



