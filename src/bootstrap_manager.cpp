#include "bootstrap_manager.hpp"
#include "to_bootstrap_connection.hpp"

#include <boost/bind.hpp>
#include <boost/intrusive_ptr.hpp>
using boost::shared_ptr;
using boost::bind;
using flint::bootstrap_manager;
namespace flint{

	bootstrap_manager::bootstrap_manager(int listen_port,char const* listen_interface)
	:m_listen_port(listen_port)
	,m_listen_interface(address::from_string(listen_interface),listen_port)
	{
		
	}

	bool bootstrap_manager::listen_on(int port,const char* net_interface)
	{
		bootstrap_manager::mutex_t::scoped_lock l(m_mutex);
		tcp::endpoint new_interface;
		if(net_interface && std::strlen(net_interface)>0)
			new_interface = tcp::endpoint(address::from_string(net_interface),port);
		else
			new_interface = tcp::endpoint(address(),port);
		m_listen_port = port;
		if(new_interface == m_listen_interface && m_listen_socket)return true;
		if(m_listen_socket)
			m_listen_socket.reset();
		
		m_listen_interface = new_interface;
		open_listen_port();
	}

	void bootstrap_manager::open_listen_port()
	{
		m_listen_socket = boost::shared_ptr<socket_acceptor>(new socket_acceptor(m_io_service));
		for(;;)
		{
			m_listen_socket->open(m_listen_interface.protocol());
			m_listen_socket->bind(m_listen_interface);
			m_listen_socket->listen();
			break;
		}
		if(m_listen_socket) async_accept();
	}
	
	void bootstrap_manager::async_accept()
	{
		shared_ptr<stream_socket> c(new stream_socket(m_io_service));
		m_listen_socket->async_accept(*c,bind(&bootstrap_manager::on_incoming_connection,this,c,boost::shared_ptr<socket_acceptor>(m_listen_socket),_1));	
	}

	void bootstrap_manager::on_incoming_connection(shared_ptr<stream_socket> const& s,shared_ptr<socket_acceptor> const& listen_socket,boost::system::error_code const& e)
	{
		if(listen_socket.unique())return;
		
		mutex_t::scoped_lock l(m_mutex);
		
		
		async_accept();
		m_incoming_connection = true;
		tcp::endpoint end = s->remote_endpoint();
		boost::shared_ptr<to_bootstrap_connection> c(new to_bootstrap_connection(*this,s));
		
		m_connections.insert(std::make_pair(s,c)); 

	}
}
