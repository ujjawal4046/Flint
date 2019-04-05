#include "bootstrap_manager.hpp"
#include "to_bootstrap_connnection.hpp"
#include <boost/bind.hpp>

namespace flint{
	to_bootstrap_connection::to_bootstrap_connection(bootstrap_manager &man,boost::shared_ptr<stream_socket> s)
		:m_socket(s)
		,m_manager(man)
		,m_recv_pos(0);
		{
			m_remote = m_socket->remote_endpoint();
			int max_receive = 32;
			m_socket->async_read_some(asio::buffer(&m_recv_buffer[m_recv_pos],max_receive),bind(&to_bootstrap_connection::on_receive_data,self(),_1,_2));
		}
	to_bootstrap_connection::on_receive_data(const boost::system::error_code &e,std::size_t bytes_trans)
		{
			bootstrap_manager::mutex_t::scoped_lock l(m_manager.m_mutex);
			if(e)
			{
				//print to err stream
			}
			
			
			check_remote_type(bytes_trans);
		}

		to_bootstrap_connection::check_remote_type(std::size_t bytes_trans)
		{
			assert(bytes_trans >= 1);
			
			switch (m_recv_buffer[0])
			{
				case 0:
					//Peer connection Ignore rest of message and reply from m_manager for allocated nodes
					
				case 1:
					//Superpeer connection. Check if keep alive and neigbour allocation
				case 2:
					//replicated bootstrap. TO DO
			}
		}

			


		
	}
}

