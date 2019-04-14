#include "bootstrap_manager.hpp"
#include "to_bootstrap_connection.hpp"

#include <boost/bind.hpp>
#include <boost/intrusive_ptr.hpp>

#include <iostream>
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
		std::cerr<<m_listen_interface.address()<<':'<<m_listen_interface.port()<<'\n';
		m_listen_socket = boost::shared_ptr<socket_acceptor>(new socket_acceptor(m_io_service));
		//for(;;)
		{
			try{
			m_listen_socket->open(m_listen_interface.protocol());
			m_listen_socket->bind(m_listen_interface);
			m_listen_socket->listen();
			std::cerr<<m_listen_socket->is_open()<<'\n';
			
			}
			catch(boost::system::system_error &e)
			{
				std::cout<<e.what()<<std::endl;
			}
		}
		
		if(m_listen_socket) async_accept();
		m_io_service.run();
	}
	
	void bootstrap_manager::async_accept()
	{
		shared_ptr<stream_socket> c(new stream_socket(m_io_service));
		m_listen_socket->async_accept(*c,bind(&bootstrap_manager::on_incoming_connection,this,c,boost::weak_ptr<socket_acceptor>(m_listen_socket),_1));	
	}

	void bootstrap_manager::on_incoming_connection(shared_ptr<stream_socket> const& s,boost::weak_ptr<socket_acceptor> const& listen_socket,boost::system::error_code const& e)
	{
		
		mutex_t::scoped_lock l(m_mutex);
		assert(listen_socket.lock() == m_listen_socket);	
		std::cout<<"came connection\n";	
		async_accept();
		m_incoming_connection = true;
		tcp::endpoint end = s->remote_endpoint();
		boost::shared_ptr<to_bootstrap_connection> c(new to_bootstrap_connection(*this,s));
		
		m_connections.insert(std::make_pair(s,c)); 

	}

	int bootstrap_manager::allocate_superpeers(std::vector<tcp::endpoint> &buffer)
	{
		mutex_t::scoped_lock l(m_mutex);
		int buffer_size = (m_superpeers.size() < bootstrap_manager::MAX_SUPERPEER_ALLOCATION)?m_superpeers.size():bootstrap_manager::MAX_SUPERPEER_ALLOCATION;
		typedef superpeer_map::right_map::const_iterator r_iterator;
		for(r_iterator r_iter = m_superpeers.right.begin(),iend = m_superpeers.right.end();r_iter != iend;r_iter++)
		{
			buffer.push_back(r_iter->second);
			--buffer_size;
			if(buffer_size <= 0)break;
		}
		return buffer.size();
	}
	bootstrap_manager:: ~bootstrap_manager()
	{
		mutex_t::scoped_lock l(m_mutex);
		m_io_service.stop();
	}
}
